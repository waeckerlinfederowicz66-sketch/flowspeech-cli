import base64
import json
from types import SimpleNamespace

import pytest

from flowspeech_cli import cli
from flowspeech_cli.client import synthesize, api_origin
from test_v1_contract import JOB, REQUEST, factory, job, response, wav_bytes


def test_client_signature_and_base64_compatibility(factory):
    core, calls, _, _ = factory([response(job())])
    result = synthesize("Hi", request_id=REQUEST, api_key="test-only",
                        http_client=core._client, download_client=core._download)
    assert base64.b64decode(result.audio_base64) == wav_bytes()
    assert result.job_id == JOB and result.request_id == REQUEST
    assert calls[0].url.path == "/api/v1/tts/jobs"


@pytest.mark.parametrize("input_kind", ["inline", "file", "segments"])
def test_cli_writes_audio_and_prints_request_id(monkeypatch, tmp_path, capsys, input_kind):
    def fake(text, **kwargs):
        assert kwargs["request_id"] == REQUEST
        if input_kind == "segments":
            assert kwargs["segments"][0]["speaker"] == "Alice" and text is None
        else:
            assert text == "Hello"
        return SimpleNamespace(audio_base64=base64.b64encode(wav_bytes()), job_id=JOB, request_id=REQUEST)
    monkeypatch.setattr(cli, "synthesize", fake)
    output = tmp_path / "result.wav"
    arguments = ["synthesize", "--out", str(output), "--request-id", REQUEST]
    if input_kind == "inline":
        arguments.append("Hello")
    else:
        path = tmp_path / "input"
        path.write_text("Hello" if input_kind == "file" else '[{"speaker":"Alice","text":"Hello","voiceName":"Kore"}]')
        arguments += ["--" + input_kind, str(path)]
    assert cli.main(arguments) == 0
    assert output.read_bytes() == wav_bytes()
    assert REQUEST in capsys.readouterr().err


def test_cli_errors_exit_nonzero(tmp_path, capsys):
    assert cli.main(["synthesize", "Hi", "--file", "conflict", "--out", str(tmp_path / "x")]) == 1
    assert "exactly one" in capsys.readouterr().err


def test_doctor_does_not_print_key(monkeypatch, capsys):
    monkeypatch.setenv("FLOWSPEECH_API_KEY", "test-only")
    assert cli.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "configured" in output and "test-only" not in output


def test_legacy_api_url_rejected():
    with pytest.raises(ValueError, match="legacy"):
        api_origin("https://flowspeech.io/api/ai/text-to-speech")


def test_compatibility_audio_helpers():
    from flowspeech_cli.audio import audio_bytes_from_response
    assert audio_bytes_from_response(audio_base64=base64.b64encode(wav_bytes()).decode(),
                                     mime_type="audio/wav") == wav_bytes()


@pytest.mark.parametrize("command", ["quota", "voices", "status", "cancel", "download"])
def test_cli_recovery_commands_never_generate(monkeypatch, tmp_path, capsys, command):
    captured = []
    class FakeClient:
        timeout = 300
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def clock(self):
            return 0
        def quota(self):
            return {"quota": {"available": 10}}
        def voices(self):
            return [{"name": "Kore"}]
        def get_job(self, job_id, **kwargs):
            assert job_id == JOB
            captured.append("get")
            return job()
        def cancel_job(self, job_id):
            assert job_id == JOB
            return job("cancelled")
        def _result(self, job):
            return job["result"]
        def download_audio(self, url, **kwargs):
            captured.append("download")
            assert kwargs["deadline"] == 300
            return wav_bytes()
    monkeypatch.setattr(cli, "V1Client", FakeClient)
    arguments = [command]
    if command in ("status", "cancel", "download"):
        arguments += ["--job-id", JOB]
    output = tmp_path / "download.wav"
    if command == "download":
        arguments += ["--out", str(output)]
    assert cli.main(arguments) == 0
    if command == "download":
        assert output.read_bytes() == wav_bytes()
        assert captured == ["get", "download"]


def test_cli_missing_key_fails_without_output(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("FLOWSPEECH_API_KEY", raising=False)
    output = tmp_path / "missing.wav"
    assert cli.main(["synthesize", "Hello", "--out", str(output), "--request-id", REQUEST]) == 1
    assert not output.exists() and "key" in capsys.readouterr().err

