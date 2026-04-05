from __future__ import annotations

import re


def _clean_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _normalize_numeric_code(code: int) -> str:
    if code in {30}:
        return "fishing"
    if code in {31, 32}:
        return "towing"
    if code in {33, 34, 53, 54, 59}:
        return "service"
    if code in {35}:
        return "military"
    if code in {36}:
        return "sailing"
    if code in {37}:
        return "pleasure"
    if 40 <= code <= 49:
        return "high_speed"
    if code in {50}:
        return "pilot"
    if code in {51}:
        return "search_rescue"
    if code in {52}:
        return "tug"
    if code in {55}:
        return "law_enforcement"
    if code in {58}:
        return "medical"
    if 60 <= code <= 69:
        return "passenger"
    if 70 <= code <= 79:
        return "cargo"
    if 80 <= code <= 89:
        return "tanker"
    if 90 <= code <= 99:
        return "other"
    return "unknown"


def normalize_vessel_type(value: str | None) -> str:
    if value is None:
        return ""
    raw = value.strip()
    if raw == "":
        return ""

    if raw.isdigit():
        return _normalize_numeric_code(int(raw))

    text = _clean_text(raw)
    if text == "":
        return ""

    keyword_map = (
        ("search rescue", "search_rescue"),
        ("rescue", "search_rescue"),
        ("sar", "search_rescue"),
        ("law enforcement", "law_enforcement"),
        ("police", "law_enforcement"),
        ("medical", "medical"),
        ("hospital", "medical"),
        ("military", "military"),
        ("navy", "military"),
        ("high speed", "high_speed"),
        ("hsc", "high_speed"),
        ("passenger", "passenger"),
        ("cargo", "cargo"),
        ("container", "cargo"),
        ("bulk", "cargo"),
        ("tanker", "tanker"),
        ("tank", "tanker"),
        ("pilot", "pilot"),
        ("fishing", "fishing"),
        ("trawler", "fishing"),
        ("sailing", "sailing"),
        ("sail", "sailing"),
        ("yacht", "pleasure"),
        ("pleasure", "pleasure"),
        ("tug", "tug"),
        ("towing", "towing"),
        ("tow", "towing"),
        ("dredg", "service"),
        ("diving", "service"),
        ("pollution", "service"),
        ("port tender", "service"),
        ("service", "service"),
        ("other", "other"),
    )
    for keyword, normalized in keyword_map:
        if keyword in text:
            return normalized

    digit_tokens = re.findall(r"\d+", text)
    if digit_tokens:
        return _normalize_numeric_code(int(digit_tokens[0]))

    return text.replace(" ", "_")
