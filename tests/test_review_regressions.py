import threading
import traceback
import contextlib
import io

import httpx
import pytest

from flowspeech_cli import _v1 as adapter
from test_v1_contract import Clock, INPUT, REQUEST, job, wav_bytes

QUOTA = {"quota": {"remaining": 10, "reserved": 0, "available": 10},
         "subscription": None, "limits": {}}


class BrokenBody(httpx.SyncByteStream):
    def __init__(self, fail_on_close=False):
        self.closed = False
        self.fail_on_close = fail_on_close

    def __iter__(self):
        yield b'{"incomplete":'
        if not self.fail_on_close:
            raise httpx.ReadError("SYNTHETIC_PRIVATE_TRANSPORT_DATA")

    def close(self):
        self.closed = True
        if self.fail_on_close:
            raise httpx.ReadError("SYNTHETIC_PRIVATE_TRANSPORT_DATA")


@pytest.mark.parametrize("status", [200, 401, 403, 429, 503])
@pytest.mark.parametrize("download", [False, True])
@pytest.mark.parametrize("fail_on_close", [False, True])
def test_interrupted_body_preserves_status_and_cooldown(status, download, fail_on_close):
    clock, calls, stream = Clock(), [], BrokenBody(fail_on_close)
    retryable = status in (200, 429, 503)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, headers={"Retry-After": "60"}, stream=stream)
        return (httpx.Response(200, content=wav_bytes()) if download
                else httpx.Response(200, json=QUOTA))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with adapter.V1Client(api_key="synthetic-test-only", http_client=http,
                              download_client=http, clock=clock, sleep=clock.sleep) as client:
            operation = (lambda: client.download_audio("https://audio.invalid/file?signature=private")) if download else client.quota
            if retryable:
                operation()
                assert len(calls) == 2 and clock.waits == [60]
            else:
                with pytest.raises(adapter.ApiError) as caught:
                    operation()
                assert caught.value.status_code == status
                assert not caught.value.retryable
                rendered = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
                assert "SYNTHETIC_PRIVATE_TRANSPORT_DATA" not in rendered
                assert len(calls) == 1 and clock.waits == []
    assert stream.closed
    if download:
        assert all("authorization" not in request.headers for request in calls)


def test_interrupted_create_retains_idempotency_key_and_body():
    clock, calls = Clock(), []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "12"}, stream=BrokenBody())
        if request.url.host == "audio.example.test":
            return httpx.Response(200, content=wav_bytes())
        return httpx.Response(200, json=job())

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with adapter.V1Client(api_key="synthetic-test-only", http_client=http,
                              download_client=http, clock=clock, sleep=clock.sleep) as client:
            client.generate(INPUT, request_id=REQUEST)
    creates = [request for request in calls if request.method == "POST"]
    assert len(creates) == 2 and clock.waits == [12]
    assert creates[0].content == creates[1].content
    assert {request.headers["Idempotency-Key"] for request in creates} == {REQUEST}


def test_cooldown_beyond_deadline_never_retries():
    clock, calls = Clock(), []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "60"}, stream=BrokenBody())

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with adapter.V1Client(api_key="synthetic-test-only", http_client=http,
                              download_client=http, clock=clock, sleep=clock.sleep, timeout=20) as client:
            with pytest.raises(adapter.ApiError) as caught:
                client.generate(INPUT, request_id=REQUEST)
    assert caught.value.code == "deadline_exceeded"
    assert caught.value.request_id == REQUEST
    assert len(calls) == 1 and clock.waits == []


def test_timed_out_client_cannot_accumulate_workers_or_queue_posts():
    entered, release = threading.Event(), threading.Event()
    calls, workers = [], []
    first = True

    def handler(request):
        nonlocal first
        calls.append(request)
        if first:
            first = False
            workers.append(threading.current_thread())
            entered.set()
            assert release.wait(2)
        return httpx.Response(200, json=QUOTA)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with adapter.V1Client(api_key="synthetic-test-only", http_client=http,
                              download_client=http, timeout=0.04) as client:
            try:
                with pytest.raises(adapter.ApiError) as caught:
                    client.quota()
                assert entered.is_set() and caught.value.code == "deadline_exceeded"
                for _ in range(3):
                    with pytest.raises(adapter.ApiError) as rejected:
                        client.generate(INPUT, request_id=REQUEST)
                    assert rejected.value.code == "request_in_progress"
                    assert rejected.value.request_id == REQUEST
                assert len(calls) == 1
                assert not http.is_closed
            finally:
                release.set()
                for worker in workers:
                    worker.join(1)
                    assert not worker.is_alive()
            assert client.quota() == QUOTA
            assert len(calls) == 2 and all(request.method == "GET" for request in calls)


@pytest.mark.parametrize("owned", [False, True])
def test_close_is_nonblocking_and_defers_only_owned_cleanup(monkeypatch, owned):
    release = threading.Event()
    workers, calls = [], []

    def handler(request):
        calls.append(request)
        workers.append(threading.current_thread())
        assert release.wait(2)
        return httpx.Response(200, json=QUOTA)

    api = httpx.Client(transport=httpx.MockTransport(handler))
    download = httpx.Client(transport=httpx.MockTransport(handler))
    if owned:
        clients = iter([api, download])
        monkeypatch.setattr(adapter.httpx, "Client", lambda **_: next(clients))
        client = adapter.V1Client(api_key="synthetic-test-only", timeout=0.04)
    else:
        client = adapter.V1Client(api_key="synthetic-test-only", timeout=0.04,
                                 http_client=api, download_client=download)
    try:
        with pytest.raises(adapter.ApiError):
            client.quota()
        client.close()
        assert not api.is_closed and not download.is_closed
        with pytest.raises(adapter.ApiError) as caught:
            client.quota()
        assert caught.value.code == "client_closed" and len(calls) == 1
    finally:
        release.set()
        for worker in workers:
            worker.join(1)
            assert not worker.is_alive()
    assert api.is_closed is owned and download.is_closed is owned
    client.close()
    api.close()
    download.close()


def test_delayed_worker_never_sends_after_caller_timeout(monkeypatch):
    release = threading.Event()
    original_thread = threading.Thread
    workers, calls = [], []

    def delayed_thread(*, target, **kwargs):
        def delayed():
            assert release.wait(2)
            target()
        worker = original_thread(target=delayed, **kwargs)
        workers.append(worker)
        return worker

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=QUOTA)

    clock = Clock()
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with adapter.V1Client(api_key="synthetic-test-only", http_client=http, download_client=http,
                              timeout=0.04, clock=clock) as client:
            try:
                with monkeypatch.context() as patch:
                    patch.setattr(adapter.threading, "Thread", delayed_thread)
                    with pytest.raises(adapter.ApiError) as caught:
                        client.generate(INPUT, request_id=REQUEST)
                assert caught.value.code == "deadline_exceeded" and not calls
            finally:
                release.set()
                for worker in workers:
                    worker.join(1)
                    assert not worker.is_alive()
            assert not calls
            assert client.quota() == QUOTA
            assert len(calls) == 1 and calls[0].method == "GET"


def test_worker_budget_is_shared_across_new_clients(monkeypatch):
    monkeypatch.setattr(adapter, "_HTTP_WORKERS", threading.BoundedSemaphore(2))
    release = threading.Event()
    calls, workers = [], []

    def handler(request):
        calls.append(request)
        workers.append(threading.current_thread())
        assert release.wait(2)
        return httpx.Response(200, json=QUOTA)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        clients = [adapter.V1Client(api_key="synthetic-test-only", http_client=http,
                                   download_client=http, timeout=0.04) for _ in range(3)]
        try:
            for client in clients[:2]:
                with pytest.raises(adapter.ApiError) as caught:
                    client.quota()
                assert caught.value.code == "deadline_exceeded"
            with pytest.raises(adapter.ApiError) as caught:
                clients[2].quota()
            assert caught.value.code == "client_busy" and len(calls) == 2
        finally:
            release.set()
            for worker in workers:
                worker.join(1)
                assert not worker.is_alive()
        assert clients[2].quota() == QUOTA
        for client in clients:
            client.close()
        assert not http.is_closed


def test_failed_thread_start_releases_both_limits(monkeypatch):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=QUOTA))) as http:
        with adapter.V1Client(api_key="synthetic-test-only", http_client=http, download_client=http) as client:
            with monkeypatch.context() as patch:
                def fail(_):
                    raise RuntimeError("synthetic thread start failure")
                patch.setattr(threading.Thread, "start", fail)
                with pytest.raises(RuntimeError, match="thread start"):
                    client.quota()
            assert client.quota() == QUOTA


@pytest.mark.parametrize("field", ["message", "code", "traceId", "job_code"])
@pytest.mark.parametrize("value_kind", ["credential", "signed_url", "nested"])
def test_error_details_do_not_echo_private_upstream_values(field, value_kind):
    key = "SYNTHETIC_REFLECTED_KEY"
    url = "https://audio.invalid/private?signature=SYNTHETIC_PRIVATE_LINK"
    value = {"credential": key, "signed_url": url, "nested": {"secret": key}}[value_kind]
    if field == "job_code":
        payload = job(status="failed", error={"code": value})
        status = 200
    else:
        payload = {"error": {"code": "rejected", "message": "rejected", "retryable": False},
                   "traceId": "trace-valid"}
        if field == "traceId":
            payload[field] = value
        else:
            payload["error"][field] = value
        status = 403
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status, json=payload))) as http:
        with adapter.V1Client(api_key=key, http_client=http, download_client=http) as client:
            with pytest.raises(adapter.ApiError) as caught:
                if field == "job_code":
                    client.generate(INPUT, request_id=REQUEST)
                else:
                    client.quota()
    rendered = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
    rendered += repr(caught.value.__dict__)
    from flowspeech_cli.cli import report_error
    output = io.StringIO()
    with contextlib.redirect_stderr(output):
        assert report_error(caught.value) == 1
    rendered += output.getvalue()
    assert key not in rendered and "SYNTHETIC_PRIVATE_LINK" not in rendered
    if field != "job_code":
        assert caught.value.status_code == 403
    if field != "traceId" and field != "job_code":
        assert caught.value.trace_id == "trace-valid"
