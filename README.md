# flowspeech-cli

Command-line client for [FlowSpeech](https://flowspeech.io/) public API v1.

```bash
pip install flowspeech-cli==0.2.0
```

Set FLOWSPEECH_API_KEY in your server or local terminal environment. The CLI never
stores or prints the key and does not accept it as a command-line argument.

```bash
flowspeech doctor
flowspeech quota
flowspeech voices
flowspeech synthesize "Welcome.[pause:2s]Let's begin." --voice Kore --out speech.wav
flowspeech synthesize --file script.txt --out narration.wav --timeout 600
```

The CLI prints request_id to stderr before generation and job_id on completion.
For recovery, pass --request-id with the original UUID and unchanged input, or set
FLOWSPEECH_REQUEST_ID. Never use a new UUID just because a response was lost.

```bash
flowspeech status --request-id UUID_FROM_PREVIOUS_RUN
flowspeech status --job-id JOB_UUID
flowspeech download --job-id JOB_UUID --out recovered.wav
flowspeech cancel --job-id JOB_UUID
```

Replace the ID placeholders with actual UUIDs. download retrieves an already
successful job and never creates a recording.

## Multiple speakers

Create a UTF-8 JSON file containing an ordered array of turns:

```json
[
  {"speaker": "Alice", "text": "Welcome.", "voiceName": "Kore"},
  {"speaker": "Bob", "text": "Thank you.", "voiceName": "Puck"}
]
```

```bash
flowspeech synthesize --segments conversation.json --out conversation.wav
```

Use exactly one of inline text, --file or --segments. --api-url remains available
but must be an HTTPS origin followed by /api/v1/tts/jobs. Legacy endpoints are
rejected. Error exit status is 1; argument errors use argparse status 2.

The Python synthesize(...) function preserves the original result fields and
adds job_id, request_id, result_url and usage. audio_base64 is encoded locally
from downloaded WAV, not returned by the v1 API. quota is None; query quota
separately. Existing audio helper functions remain available.

## API v1 behavior

An active paid Basic, Pro or Scale subscription and a FlowSpeech API key are
required; trials do not include API generation. Keep FLOWSPEECH_API_KEY server-side.
See [public API documentation](https://flowspeech.io/docs/public-api).

Generation submits POST /api/v1/tts/jobs with {"input": ...} and one UUID
Idempotency-Key, waits through queued/running/merging/settling, then downloads
result.url after success. A 200 response alone does not mean generation succeeded.
Single input uses mode/text/voiceName. Multi input uses mode/segments, where each
turn contains speaker, text and voiceName. Model, source, speed and format options
are unsupported and must not be sent.

The default total deadline is 300 seconds, polling is at least five seconds, and
longer Retry-After values (seconds or HTTP dates) are honored. Transient transport
failures, 429, and explicitly retryable 5xx errors get at most two retries.
Create retries preserve the UUID and exact body. A deadline stops local waiting,
not the server job; use the saved IDs for recovery or explicit cancellation.

Errors expose status_code, code, retryable, trace_id, request_id, job_id and
result_url where available. Failed and cancelled jobs raise errors. Deleted
success results are reported as result_deleted, not as empty audio.

Audio is a separately downloaded, validated WAV (24000 Hz, mono, 16 bit).
Validation checks the entire RIFF size, chunk bounds/padding, exactly one PCM
format/data pair, byte rate 48000, block alignment 2 and nonempty complete samples.
Malformed audio raises invalid_audio with request/job IDs and the existing result
URL preserved; it does not trigger another recording.
Downloads use HTTPS without API Authorization, cookies, or default client
credentials, including across redirects. API redirects are rejected. Downloads
are bounded to 64 MiB by default. A download retry never submits another recording.
Anyone holding a result URL can access the recording; treat links as sensitive.

GET /api/v1/quota returns quota.remaining/reserved/available plus subscription
and limits. GET /api/v1/voices
returns voices. Recovery uses GET /api/v1/tts/jobs?requestId=UUID; status and cancel
use /api/v1/tts/jobs/{UUID} and /api/v1/tts/jobs/{UUID}/cancel.

## Development

```bash
python -m pip install -e ".[test]" build
python -m pytest -q
python -m build
```

See PROVENANCE.md for verified 0.1.0 wheel provenance and RELEASE.md for the
coordinator's release steps. No upstream source repository URL is assumed.

