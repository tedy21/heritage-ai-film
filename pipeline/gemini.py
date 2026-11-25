"""Thin REST client for the Gemini API (text + TTS). Using plain HTTP keeps
the dependency list short and makes every request visible in one place."""
from __future__ import annotations

import base64
import os
import re

import requests

from .common import RetryableError, raise_for_http

BASE = "https://generativelanguage.googleapis.com/v1beta"


def _headers() -> dict:
    return {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}


def list_models() -> list[str]:
    r = requests.get(f"{BASE}/models", headers=_headers(), params={"pageSize": 200}, timeout=30)
    raise_for_http(r)
    return [m["name"].removeprefix("models/") for m in r.json().get("models", [])]


def generate_text(model: str, prompt: str, temperature: float = 0.7) -> tuple[str, dict]:
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    try:
        r = requests.post(f"{BASE}/models/{model}:generateContent", headers=_headers(), json=body, timeout=120)
    except requests.RequestException as e:
        raise RetryableError(str(e))
    raise_for_http(r)
    data = r.json()
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    return text, data.get("usageMetadata", {})


def tts(model: str, text: str, voice: str) -> tuple[bytes, int]:
    """Returns (raw 16-bit mono PCM, sample_rate)."""
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    try:
        r = requests.post(f"{BASE}/models/{model}:generateContent", headers=_headers(), json=body, timeout=180)
    except requests.RequestException as e:
        raise RetryableError(str(e))
    raise_for_http(r)
    data = r.json()
    try:
        part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    except (KeyError, IndexError):
        # Empty candidates happen intermittently with TTS; worth a retry.
        raise RetryableError(f"no audio in response: {str(data)[:300]}")
    m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
    return base64.b64decode(part["data"]), int(m.group(1)) if m else 24000
