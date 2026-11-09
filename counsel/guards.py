"""Text d1 can't judge doesn't leave. An encoded message can't be scored, so it stays on device."""
import re

OPAQUE = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/=_-]{32,}(?![A-Za-z0-9+/=_-])")


def looks_encoded(text):
    """True for a long opaque string, or text spelled out one letter at a time."""
    for match in OPAQUE.finditer(text):
        token = match.group()
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            return True
    words = re.findall(r"[^\W\d_]+", text)
    return len(words) >= 12 and sum(len(w) == 1 for w in words) / len(words) > 0.4
