from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from ._v1 import ApiError, V1Client, make_input, safe_url

DEFAULT_API_URL = "https://flowspeech.io/api/v1/tts/jobs"
DEFAULT_VOICE = "Kore"
DEFAULT_RETRIES = 2
FlowSpeechError = ApiError


@dataclass(frozen=True)
class SynthesisResult:
    audio_base64: str
    mime_type: str
    sample_rate: int = 24000
    num_channels: int = 1
    bits_per_sample: int = 16
    quota: dict[str, Any] | None = None
    job_id: str | None = None
    request_id: str | None = None
    result_url: str | None = None
    usage: dict[str, Any] | None = None


def api_origin(api_url):
    safe_url(api_url)
    suffix = "/api/v1/tts/jobs"
    if not api_url.endswith(suffix):
        raise ValueError("--api-url must end with /api/v1/tts/jobs; legacy endpoints are unsupported")
    return safe_url(api_url[:-len(suffix)], base=True)


def synthesize(text: str | None = None, *, voice: str = DEFAULT_VOICE,
               api_url: str = DEFAULT_API_URL, timeout: float = 300,
               retries: int = DEFAULT_RETRIES, api_key: str | None = None,
               request_id: str | None = None, segments=None,
               http_client=None, download_client=None) -> SynthesisResult:
    with V1Client(api_key=api_key, base_url=api_origin(api_url), timeout=timeout,
                  max_retries=retries, http_client=http_client, download_client=download_client,
                  user_agent="flowspeech-cli/0.2.0") as client:
        job, audio, request_id = client.generate(make_input(text, voice, segments), request_id=request_id)
    return SynthesisResult(base64.b64encode(audio).decode("ascii"), "audio/wav",
                           job_id=job["id"], request_id=request_id,
                           result_url=job["result"]["url"], usage=job["usage"])

