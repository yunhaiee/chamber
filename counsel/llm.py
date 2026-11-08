"""The three model clients: LFM3 (the work), d1 (the decisions), Claude (public research).

Every prompt is built by the caller from the requesting person's own material.
Nothing here keeps state between calls.
"""
import json
import os
import socket
import time

import httpx

LOCAL_API = os.environ.get("SH_LOCAL_API", "ollama")  # ollama | openai
LOCAL_BASE = os.environ.get("SH_LOCAL_BASE", "http://127.0.0.1:11434")
LOCAL_MODEL = os.environ.get("SH_LOCAL_MODEL", "lfm3:1.7b")
D1_BASE = os.environ.get("SH_D1_BASE", "http://127.0.0.1:9931")
CLOUD_MODEL = "claude-opus-5-5"
STANDIN_MODEL = "qwen3:8b"
CLOUD_HOST = os.environ.get("SH_CLOUD_HOST", "api.anthropic.com")

OPTIONS = {"temperature": 0, "seed": 7, "num_predict": 900}


class LocalError(Exception):
    """Infrastructure failure on the box. Never counted as a graded result."""


class CloudError(Exception):
    pass


def first_json(text):
    """Read the first complete JSON object from a reply. None on failure."""
    if not text:
        return None
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = decoder.raw_decode(text[start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        start = text.find("{", start + 1)
    return None


def local_chat(system, user, model=None, timeout=120):
    """Call the local model. Returns (raw_text, ms). Raises LocalError on infra failure."""
    model = model or LOCAL_MODEL
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": user}
    ]
    t = time.time()
    try:
        if LOCAL_API == "openai":
            r = httpx.post(
                f"{LOCAL_BASE}/v1/chat/completions",
                json={"model": model, "messages": messages, "temperature": 0, "seed": 7, "max_tokens": 900},
                timeout=timeout,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        else:
            r = httpx.post(
                f"{LOCAL_BASE}/api/chat",
                json={"model": model, "messages": messages, "stream": False, "think": False, "options": OPTIONS},
                timeout=timeout,
            )
            r.raise_for_status()
            text = r.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise LocalError(f"{type(e).__name__}: {e}") from e
    return text or "", int((time.time() - t) * 1000)


def d1_decide(state, questions, timeout=60):
    """One call to d1 on the box. Returns (answers, ms). Raises LocalError."""
    t = time.time()
    try:
        r = httpx.post(f"{D1_BASE}/v1/systemone", json={"state": state, "questions": questions}, timeout=timeout)
        r.raise_for_status()
        return r.json()["answers"], int((time.time() - t) * 1000)
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise LocalError(f"{type(e).__name__}: {e}") from e


def has_cloud_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def cloud_label():
    return CLOUD_MODEL if has_cloud_key() else f"{STANDIN_MODEL} stand-in"


def cloud_online(timeout=1.5):
    """A real socket check to the cloud host, in stand-in mode as well."""
    try:
        with socket.create_connection((CLOUD_HOST, 443), timeout=timeout):
            return True
    except OSError:
        return False


_client = None


def cloud_chat(system, user, timeout=120):
    """Call the cloud model. Only router.send_to_cloud may call this. Returns (text, ms)."""
    global _client
    t = time.time()
    if not has_cloud_key():
        try:
            text, _ = local_chat(system, user, model=STANDIN_MODEL, timeout=timeout)
        except LocalError as e:
            raise CloudError(str(e)) from e
        return text, int((time.time() - t) * 1000)

    import anthropic

    if _client is None:
        _client = anthropic.Anthropic(timeout=timeout)
    try:
        r = _client.beta.messages.create(
            model=CLOUD_MODEL,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIError as e:
        raise CloudError(f"{type(e).__name__}: {e}") from e
    if r.stop_reason == "refusal":
        raise CloudError("refusal")
    text = "".join(b.text for b in r.content if b.type == "text")
    return text, int((time.time() - t) * 1000)
