from __future__ import annotations
import re

_PHONE_RE = re.compile(r"^\+?\d{10,15}$")

def is_phone(text: str) -> bool:
    return bool(_PHONE_RE.match(text.strip()))

def parse_guests(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    n = int(text)
    if 1 <= n <= 12:
        return n
    return None
