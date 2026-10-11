"""Parser for SMS Interrupções raw HTML/JavaScript data."""
from __future__ import annotations

import html as html_mod
import json
import re

RE_LOCATIONS_START = re.compile(r"\blocations\s*=\s*\[")
RE_NUM = re.compile(r"^-?\d+(?:\.\d+)?")
RE_HEX = re.compile(r"^#[0-9A-Fa-f]{3,8}")
RE_LITERAL = re.compile(r"^(?:null|undefined|true|false)\b", re.IGNORECASE)

KEYS = ["lat", "lon", "zona", "detalhes", "color", "inicio", "reabertura"]


def _find_matching_bracket(text: str, start_index: int) -> int | None:
    """Find the closing ']' matching the '[' at start_index, skipping quoted strings."""
    depth = 0
    in_quote = None
    escape = False

    for i in range(start_index, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if in_quote:
            if ch == in_quote:
                in_quote = None
            continue

        if ch in ("'", '"', '`'):
            in_quote = ch
            continue

        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i

    return None


def _parse_js_tokens(array_content: str) -> list:
    """Extract individual tokens (strings, numbers, hex, null) from a JS array body."""
    tokens = []
    idx = 0
    n = len(array_content)

    while idx < n:
        ch = array_content[idx]

        # Whitespace and separators
        if ch in (" ", "\t", "\r", "\n", ","):
            idx += 1
            continue

        # Quoted strings
        if ch in ("'", '"', '`'):
            quote = ch
            idx += 1
            buf = []
            while idx < n:
                c = array_content[idx]
                if c == "\\" and idx + 1 < n:
                    buf.append(array_content[idx + 1])
                    idx += 2
                    continue
                if c == quote:
                    idx += 1
                    break
                buf.append(c)
                idx += 1
            tokens.append(html_mod.unescape("".join(buf)))
            continue

        # Numbers
        sub = array_content[idx:]
        m_num = RE_NUM.match(sub)
        if m_num:
            val_str = m_num.group(0)
            tokens.append(float(val_str) if "." in val_str else int(val_str))
            idx += len(val_str)
            continue

        # Hex colors (#FFFFFF)
        m_hex = RE_HEX.match(sub)
        if m_hex:
            tokens.append(m_hex.group(0))
            idx += len(m_hex.group(0))
            continue

        # JS literals (null, undefined, booleans)
        m_lit = RE_LITERAL.match(sub)
        if m_lit:
            lit = m_lit.group(0).lower()
            if lit in ("null", "undefined"):
                tokens.append(None)
            else:
                tokens.append(lit == "true")
            idx += len(m_lit.group(0))
            continue

        # Skip unrecognized characters
        idx += 1

    return tokens


def extract_locations_full_from_html(html_text: str) -> list[dict]:
    """Extract structured interruption items from raw website HTML."""
    if not html_text:
        return []

    match = RE_LOCATIONS_START.search(html_text)
    if not match:
        return []

    outer_start = match.end() - 1  # Index of the first '['
    outer_end = _find_matching_bracket(html_text, outer_start)
    if outer_end is None:
        return []

    outer_text = html_text[outer_start + 1 : outer_end]

    # Find each inner array [...] safely
    results = []
    idx = 0
    while idx < len(outer_text):
        if outer_text[idx] == "[":
            inner_end = _find_matching_bracket(outer_text, idx)
            if inner_end is not None:
                inner_body = outer_text[idx + 1 : inner_end]
                tokens = _parse_js_tokens(inner_body)

                if tokens:
                    item = {}
                    for j, tok in enumerate(tokens):
                        if j < len(KEYS):
                            item[KEYS[j]] = tok
                        else:
                            item[f"extra_{j - len(KEYS) + 1}"] = tok
                    results.append(item)

                idx = inner_end + 1
                continue
        idx += 1

    return results
