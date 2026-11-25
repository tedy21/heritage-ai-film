"""Thin REST client for Cloudflare Workers AI image models.

FLUX.1 schnell takes a JSON body. FLUX.2 models take multipart form data and
accept reference images (input_image_0..3), which is how keyframes are
conditioned on the golden reference sheet.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

from .common import RetryableError, raise_for_http


def _url(model: str) -> str:
    return f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/ai/run/{model}"


def _auth() -> dict:
    return {"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}


def _image_from(resp) -> bytes:
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return resp.content
    data = resp.json()
    if not data.get("success", True):
        raise RuntimeError(f"cloudflare error: {data.get('errors')}")
    img = data.get("result", {}).get("image")
    if not img:
        raise RetryableError(f"no image in response: {str(data)[:300]}")
    return base64.b64decode(img)


def generate(model: str, prompt: str, *, seed: int, width: int = 1024, height: int = 1024,
             steps: int = 4, refs: list[Path] | None = None) -> bytes:
    try:
        if "flux-2" in model:
            form = {"prompt": (None, prompt), "seed": (None, str(seed)),
                    "width": (None, str(width)), "height": (None, str(height)),
                    "steps": (None, str(steps))}
            for i, ref in enumerate((refs or [])[:4]):
                form[f"input_image_{i}"] = (ref.name, ref.read_bytes(), "image/jpeg")
            r = requests.post(_url(model), headers=_auth(), files=form, timeout=180)
        else:
            body = {"prompt": prompt, "steps": min(steps, 8), "seed": seed}
            r = requests.post(_url(model), headers=_auth(), json=body, timeout=180)
    except requests.RequestException as e:
        raise RetryableError(str(e))
    raise_for_http(r)
    return _image_from(r)


def verify_token() -> dict:
    r = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=_auth(), timeout=30)
    raise_for_http(r)
    return r.json()
