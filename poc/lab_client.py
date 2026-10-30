"""Small helper shared by the PoC scripts: a logged-in requests session."""
import re
import sys

import requests

BASE = "http://127.0.0.1:5000"


def _guard(base):
    if not (base.startswith("http://127.0.0.1") or base.startswith("http://localhost")):
        sys.exit("Refusing to run: PoCs may only target a local InkPost instance.")


def csrf(session, url):
    m = re.search(r'name="csrf_token" value="([^"]+)"', session.get(url).text)
    return {"csrf_token": m.group(1)} if m else {}


def login(username, password, base=BASE):
    _guard(base)
    s = requests.Session()
    r = s.post(f"{base}/login", data={"username": username, "password": password, **csrf(s, f"{base}/login")})
    if "Log out" not in r.text:
        sys.exit(f"Login as {username} failed (status {r.status_code}).")
    return s
