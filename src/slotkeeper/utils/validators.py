from __future__ import annotations
import re

PHONE_DIGITS_RE = re.compile(r"\d+")


def normalize_phone(raw: str) -> str | None:
    if not raw:
        return None

    digits = "".join(PHONE_DIGITS_RE.findall(raw))

    if len(digits) != 11:
        return None

    if digits.startswith("8"):
        digits = "7" + digits[1:]
    elif digits.startswith("7"):
        pass
    else:
        return None

    return "+7" + digits[1:]


def is_phone(text: str) -> bool:
    return normalize_phone(text) is not None

def parse_guests(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    n = int(text)
    if 1 <= n <= 12:
        return n
    return None
