"""Text d1 can't judge doesn't leave. An encoded or scrambled message can't be scored, so it stays on device."""
import re

COMMON = set("""
a an the and or but if of to in on at by for from with without as is are was were be been being it its this that these those
i we you he she they our your their my his her not no do does did done have has had will would can could should may might must
what when where which who how why there here after before under over about into than then also any each all
""".split())
OPAQUE = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/=_-]{32,}(?![A-Za-z0-9+/=_-])")
WINDOW = 12


def looks_encoded(text):
    """True for long opaque strings, or a run of words with almost no ordinary English in it."""
    for match in OPAQUE.finditer(text):
        token = match.group()
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            return True
    words = [w.lower() for w in re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", text)]
    if len(words) >= WINDOW and sum(len(w) == 1 for w in words) / len(words) > 0.4:
        return True
    for i in range(len(words) - WINDOW + 1):
        window = words[i:i + WINDOW]
        # A table repeats its row and column labels. Scrambled prose doesn't repeat.
        if sum(w in COMMON for w in window) <= 1 and len(set(window)) >= WINDOW * 0.75:
            return True
    return False
