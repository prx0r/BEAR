"""Free PNG rendering for mermaid diagrams via mermaid.ink (public, keyless).

Verified 2026-09-10: GET https://mermaid.ink/img/<base64url> -> JPEG/PNG.
No local chromium needed. Usage: python3 -m mimic.render IN.mmd OUT.png
"""
import base64
import os
import sys
import urllib.request


def render_file(src: str, dest: str, timeout: int = 60) -> dict:
    raw = open(src, "rb").read()
    code = base64.urlsafe_b64encode(raw).decode()
    url = f"https://mermaid.ink/img/{code}"
    req = urllib.request.Request(url, headers={"User-Agent": "mimichart/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if len(data) < 500:
        return {"ok": False, "error": f"suspiciously small ({len(data)}B)"}
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    open(dest, "wb").write(data)
    return {"ok": True, "bytes": len(data), "dest": dest}


if __name__ == "__main__":
    print(render_file(sys.argv[1], sys.argv[2]))
