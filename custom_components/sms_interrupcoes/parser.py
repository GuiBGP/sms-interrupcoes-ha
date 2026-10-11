"""Parser for SMS Interrupções raw HTML/JavaScript data."""
from __future__ import annotations

import html as html_mod
import re

RE_LOCATIONS = re.compile(r"\blocations\s*=\s*\[(.*?)\];\s*for\b", re.DOTALL)
KEYS = ["lat", "lon", "zona", "detalhes", "color", "inicio", "reabertura"]


def extract_locations_full_from_html(html_text: str) -> list[dict]:
    """Parse JavaScript locations = [ ... ] from SMS Setúbal."""
    if not html_text:
        return []

    # 1. Match the exact array body between 'locations = [' and ']; for'
    match = RE_LOCATIONS.search(html_text)
    if not match:
        # Fallback to general brackets match if script structure varies slightly
        alt_match = re.search(r"\blocations\s*=\s*(\[.*?\])\s*;", html_text, re.DOTALL)
        if not alt_match:
            return []
        array_text = alt_match.group(1).strip()
    else:
        array_text = f"[{match.group(1).strip()}]"

    # If the array is empty: locations = [];
    inner_content = array_text.strip("[]").strip()
    if not inner_content:
        return []

    # 2. Extract inner [ ... ] elements safely by handling strings and quotes
    inner_items = []
    depth = 0
    in_quote = None
    escape = False
    current_start = None

    for idx, ch in enumerate(array_text):
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
        elif ch in ("'", '"'):
            in_quote = ch
            continue

        if ch == "[":
            depth += 1
            if depth == 2:
                current_start = idx
        elif ch == "]":
            if depth == 2 and current_start is not None:
                inner_items.append(array_text[current_start : idx + 1])
                current_start = None
            depth -= 1

    results = []

    # 3. Tokenize each inner entry
    for item_str in inner_items:
        # Strip enclosing [ and ]
        content = item_str.strip()[1:-1].strip()
        tokens = []
        t_idx = 0
        t_len = len(content)

        while t_idx < t_len:
            c = content[t_idx]

            # Whitespace / commas
            if c in (" ", "\t", "\r", "\n", ","):
                t_idx += 1
                continue

            # Strings: '...' or "..."
            if c in ("'", '"'):
                q = c
                t_idx += 1
                buf = []
                while t_idx < t_len:
                    ch_cur = content[t_idx]
                    if ch_cur == "\\" and t_idx + 1 < t_len:
                        buf.append(content[t_idx + 1])
                        t_idx += 2
                        continue
                    if ch_cur == q:
                        t_idx += 1
                        break
                    buf.append(ch_cur)
                    t_idx += 1
                tokens.append(html_mod.unescape("".join(buf)).strip())
                continue

            # Numbers & Floats
            m_num = re.match(r"^-?\d+(?:\.\d+)?", content[t_idx:])
            if m_num:
                num_str = m_num.group(0)
                tokens.append(float(num_str) if "." in num_str else int(num_str))
                t_idx += len(num_str)
                continue

            # Hex colors or unquoted words
            m_word = re.match(r"^[^,\s\]]+", content[t_idx:])
            if m_word:
                word_str = m_word.group(0).strip()
                tokens.append(word_str)
                t_idx += len(m_word.group(0))
                continue

            t_idx += 1

        if tokens:
            entry = {}
            for j, tok in enumerate(tokens):
                if j < len(KEYS):
                    entry[KEYS[j]] = tok
                else:
                    entry[f"extra_{j - len(KEYS) + 1}"] = tok
            results.append(entry)

    return results
