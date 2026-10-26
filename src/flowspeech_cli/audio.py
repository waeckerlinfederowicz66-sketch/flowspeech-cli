from __future__ import annotations

import base64
import struct


DEFAULT_SAMPLE_RATE = 24000
DEFAULT_NUM_CHANNELS = 1
DEFAULT_BITS_PER_SAMPLE = 16


def decode_base64_audio(value: str) -> bytes:
    if not value:
        raise ValueError("No audio data returned")

    normalized = value.strip()
    if normalized.startswith("data:"):
        _, _, normalized = normalized.partition(",")

    try:
        return base64.b64decode(normalized, validate=True)
    except Exception as exc:
        raise ValueError("Audio data is not valid base64") from exc


def pcm_to_wav(
    pcm_data: bytes,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    num_channels: int = DEFAULT_NUM_CHANNELS,
    bits_per_sample: int = DEFAULT_BITS_PER_SAMPLE,
) -> bytes:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if num_channels <= 0:
        raise ValueError("num_channels must be positive")
    if bits_per_sample not in (8, 16, 24, 32):
        raise ValueError("bits_per_sample must be one of 8, 16, 24, 32")

    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_data)

    header = b"".join(
        [
            b"RIFF",
            struct.pack("<I", 36 + data_size),
            b"WAVE",
            b"fmt ",
            struct.pack("<I", 16),
            struct.pack("<H", 1),
            struct.pack("<H", num_channels),
            struct.pack("<I", sample_rate),
            struct.pack("<I", byte_rate),
            struct.pack("<H", block_align),
            struct.pack("<H", bits_per_sample),
            b"data",
            struct.pack("<I", data_size),
        ]
    )
    return header + pcm_data


def audio_bytes_from_response(
    *,
    audio_base64: str,
    mime_type: str,
    sample_rate: int | None = None,
    num_channels: int | None = None,
    bits_per_sample: int | None = None,
) -> bytes:
    raw_audio = decode_base64_audio(audio_base64)
    normalized_mime = (mime_type or "").lower()

    if "wav" in normalized_mime or "mpeg" in normalized_mime or "mp3" in normalized_mime:
        return raw_audio

    if "pcm" in normalized_mime or "l16" in normalized_mime:
        return pcm_to_wav(
            raw_audio,
            sample_rate=sample_rate or DEFAULT_SAMPLE_RATE,
            num_channels=num_channels or DEFAULT_NUM_CHANNELS,
            bits_per_sample=bits_per_sample or DEFAULT_BITS_PER_SAMPLE,
        )

    raise ValueError(f"Unsupported audio format: {mime_type or 'unknown'}")
