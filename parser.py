
import re
import html as html_mod

def extract_locations_full_from_html(html_text: str):
    """
    Parse the JavaScript `locations = [ ... ]` from an HTML page and return
    a list of dicts with keys:
      lat, lon, zona, detalhes, color, inicio, reabertura
    Any extra tokens are mapped to extra_1, extra_2, ...
    """
    m = re.search(r"\blocations\s*=\s*(\[)", html_text)
    if not m:
        return []

    start = m.start(1)

    depth = 0
    end = None
    for i, ch in enumerate(html_text[start:], start):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        return []
    outer = html_text[start:end+1]

    inner_arrays = []
    depth = 0
    current_start = None
    for i, ch in enumerate(outer):
        if ch == '[':
            depth += 1
            if depth == 2:
                current_start = i
        elif ch == ']':
            if depth == 2 and current_start is not None:
                inner_arrays.append(outer[current_start:i+1])
                current_start = None
            depth -= 1

    results = []
    keys = ['lat', 'lon', 'zona', 'detalhes', 'color', 'inicio', 'reabertura']

    for arr in inner_arrays:
        tokens = []
        idx = 0
        while idx < len(arr):
            ch = arr[idx]
            if ch in "\"'":
                quote = ch
                idx += 1
                buf = ''
                while idx < len(arr):
                    c = arr[idx]
                    if c == '\\' and idx + 1 < len(arr):
                        buf += arr[idx+1]
                        idx += 2
                        continue
                    if c == quote:
                        break
                    buf += c
                    idx += 1
                tokens.append(html_mod.unescape(buf))
                idx += 1
            elif ch.isdigit() or (ch == '-' and idx + 1 < len(arr) and arr[idx+1].isdigit()):
                import re as _re
                mnum = _re.match(r"-?\d+(?:\.\d+)?", arr[idx:])
                if mnum:
                    tokens.append(float(mnum.group(0)))
                    idx += len(mnum.group(0))
                else:
                    idx += 1
            elif ch == '#':
                import re as _re
                mhex = _re.match(r"#[0-9A-Fa-f]{3,8}", arr[idx:])
                if mhex:
                    tokens.append(mhex.group(0))
                    idx += len(mhex.group(0))
                else:
                    idx += 1
            else:
                idx += 1

        item = {}
        for j, tok in enumerate(tokens):
            if j < len(keys):
                item[keys[j]] = tok
            else:
                item[f'extra_{j - len(keys) + 1}'] = tok
        if item:
            results.append(item)

    return results
