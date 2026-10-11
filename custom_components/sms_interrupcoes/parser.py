"""Parser for SMS Interrupções raw HTML/JavaScript data."""
from __future__ import annotations

import html as html_mod
import re

RE_NUM = re.compile(r"^-?\d+(?:\.\d+)?")
RE_HEX = re.compile(r"^#[0-9A-Fa-f]{3,8}")
KEYS = ["lat", "lon", "zona", "detalhes", "color", "inicio", "reabertura"]


def extract_locations_full_from_html(html_text: str) -> list[dict]:
    """Parse the JavaScript locations = [ ... ] from an HTML page."""
    if not html_text:
        return []

    # 1. Match 'locations = [' or 'locations=[' or 'var locations = ['
    m = re.search(r"\blocations\s*=\s*(\[)", html_text)
    if not m:
        return []

    start = m.start(1)

    # 2. Extract outer bracket range matching your original bracket counting
    depth = 0
    end = None
    for i, ch in enumerate(html_text[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end is None:
        return []

    outer = html_text[start : end + 1]

    # 3. Slice out depth-2 inner arrays: [[...], [...]]
    inner_arrays = []
    depth = 0
    current_start = None
    for i, ch in enumerate(outer):
        if ch == "[":
            depth += 1
            if depth == 2:
                current_start = i
        elif ch == "]":
            if depth == 2 and current_start is not None:
                inner_arrays.append(outer[current_start : i + 1])
                current_start = None
            depth -= 1

    results = []

    # 4. Tokenize each inner array
    for arr in inner_arrays:
        tokens = []
        idx = 0
        arr_len = len(arr)

        while idx < arr_len:
            ch = arr[idx]

            # Single or double quoted strings
            if ch in ("'", '"'):
                quote = ch
                idx += 1
                buf = []
                while idx < arr_len:
                    c = arr[idx]
                    if c == "\\" and idx + 1 < arr_len:
                        buf.append(arr[idx + 1])
                        idx += 2
                        continue
                    if c == quote:
                        break
                    buf.append(c)
                    idx += 1
                tokens.append(html_mod.unescape("".join(buf)))
                idx += 1

            # Numbers (float / int)
            elif ch.isdigit() or (ch == "-" and idx + 1 < arr_len and arr[idx + 1].isdigit()):
                mnum = RE_NUM.match(arr[idx:])
                if mnum:
                    val_str = mnum.group(0)
                    tokens.append(float(val_str) if "." in val_str else int(val_str))
                    idx += len(val_str)
                else:
                    idx += 1

            # Hex colors (e.g. #FF0000)
            elif ch == "#":
                mhex = RE_HEX.match(arr[idx:])
                if mhex:
                    tokens.append(mhex.group(0))
                    idx += len(mhex.group(0))
                else:
                    idx += 1

            else:
                idx += 1

        # Map tokens to dict keys
        item = {}
        for j, tok in enumerate(tokens):
            if j < len(KEYS):
                item[KEYS[j]] = tok
            else:
                item[f"extra_{j - len(KEYS) + 1}"] = tok

        if item:
            results.append(item)

    return results
