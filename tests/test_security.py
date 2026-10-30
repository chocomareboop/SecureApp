"""Security regression tests, one block per threat in the risk register.

On the vulnerable baseline (tag v0-vulnerable) these tests FAIL — that is the
evidence the vulnerabilities exist. Each fix PR makes its block pass.
"""
import io
import os
import struct
import subprocess

from .conftest import NATIVE_CLI, PNG_1X1, login, make_ink, post_by_title, post_form, user_id


# --------------------------------------------------------------------------- #
# VULN-1  Buffer overflow in native .ink parser (CWE-120)
# --------------------------------------------------------------------------- #
def test_bof_overlong_title_cannot_forge_author_or_publish(app, client):
    login(client, "bob")
    admin_id = user_id(app, "admin")
    # 64-byte title, then 8 bytes that land on is_published=1 and author_id=admin.
    title = b"Official announcement".ljust(64, b" ") + struct.pack("<ii", 1, admin_id)
    data = {"ink_file": (io.BytesIO(make_ink(title, b"news")), "evil.ink")}
    post_form(client, "/import", "/import", data, content_type="multipart/form-data")
    forged = post_by_title(app, "Official announcement")
    assert forged is None or (forged.author_id == user_id(app, "bob") and not forged.is_published)


def test_bof_huge_title_does_not_crash_parser(tmp_path):
    sample = tmp_path / "crash.ink"
    sample.write_bytes(make_ink(b"A" * 600))
    proc = subprocess.run([NATIVE_CLI, str(sample), "3"], capture_output=True, text=True)
    # A negative return code means the process died from a signal (SIGSEGV/SIGABRT).
    assert proc.returncode >= 0, f"parser crashed with signal {-proc.returncode}"
    assert "REJECTED" in proc.stdout


# --------------------------------------------------------------------------- #
# VULN-2  OS command injection in cover inspector (CWE-78)
# --------------------------------------------------------------------------- #
def test_cover_filename_is_not_executed_by_shell(app, client):
    login(client, "alice")
    evil_name = "x.png;echo inkpwn$((40+2));#.png"
    data = {"title": "Injection test", "body": "b", "cover": (io.BytesIO(PNG_1X1), evil_name)}
    post_form(client, "/write", "/write", data, content_type="multipart/form-data")
    post = post_by_title(app, "Injection test")
    assert post is not None
    r = post_form(client, f"/post/{post.id}/edit", f"/post/{post.id}/cover-info")
    assert "inkpwn42" not in r.get_data(as_text=True)


def test_cover_stored_under_server_generated_name(app, client):
    login(client, "alice")
    data = {"title": "Name test", "body": "b", "cover": (io.BytesIO(PNG_1X1), "my holiday photo.png")}
    post_form(client, "/write", "/write", data, content_type="multipart/form-data")
    post = post_by_title(app, "Name test")
    assert post.cover_filename != "my holiday photo.png"
    assert os.path.basename(post.cover_filename) == post.cover_filename


def test_non_image_cover_rejected(app, client):
    login(client, "alice")
    data = {"title": "Fake image", "body": "b", "cover": (io.BytesIO(b"#!/bin/sh\necho hi\n"), "script.png")}
    post_form(client, "/write", "/write", data, content_type="multipart/form-data")
    assert post_by_title(app, "Fake image") is None


# --------------------------------------------------------------------------- #
# VULN-3  IDOR on posts (CWE-639)
# --------------------------------------------------------------------------- #
def test_idor_cannot_open_other_users_draft_in_editor(app, client):
    login(client, "bob")
    draft = post_by_title(app, "Budget 2026 — confidential draft")
    r = client.get(f"/post/{draft.id}/edit")
    assert r.status_code in (403, 404)
    assert "PKR 450,000" not in r.get_data(as_text=True)


def test_idor_api_hides_other_users_draft(app, client):
    login(client, "bob")
    draft = post_by_title(app, "Budget 2026 — confidential draft")
    r = client.get(f"/api/posts/{draft.id}")
    assert r.status_code == 404
    assert "PKR 450,000" not in r.get_data(as_text=True)


def test_idor_cannot_edit_other_users_post(app, client):
    login(client, "bob")
    post = post_by_title(app, "Welcome to the Robotics Society blog")
    r = post_form(client, "/write", f"/post/{post.id}/edit", {"title": "Hacked by bob", "body": "x"})
    assert r.status_code in (403, 404)
    assert post_by_title(app, "Hacked by bob") is None


def test_idor_cannot_delete_or_unpublish_other_users_post(app, client):
    login(client, "bob")
    post = post_by_title(app, "Welcome to the Robotics Society blog")
    assert post_form(client, "/write", f"/post/{post.id}/delete").status_code in (403, 404)
    assert post_form(client, "/write", f"/post/{post.id}/publish").status_code in (403, 404)
    after = post_by_title(app, "Welcome to the Robotics Society blog")
    assert after is not None and after.is_published


# --------------------------------------------------------------------------- #
# VULN-4  CSRF (CWE-352)
# --------------------------------------------------------------------------- #
def test_csrf_email_change_without_token_is_rejected(app, client):
    login(client, "alice")
    r = client.post("/settings/email", data={"email": "attacker@evil.test"})
    assert r.status_code == 400
    assert "attacker@evil.test" not in client.get("/settings").get_data(as_text=True)


def test_csrf_delete_post_without_token_is_rejected(app, client):
    login(client, "alice")
    post = post_by_title(app, "Welcome to the Robotics Society blog")
    assert client.post(f"/post/{post.id}/delete").status_code == 400
    assert post_by_title(app, "Welcome to the Robotics Society blog") is not None


def test_session_cookie_flags(client):
    r = login(client, "alice")
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


# --------------------------------------------------------------------------- #
# VULN-5  Clickjacking (CWE-1021)
# --------------------------------------------------------------------------- #
def test_pages_refuse_to_be_framed(client):
    login(client, "alice")
    for url in ("/", "/settings", "/login"):
        r = client.get(url)
        assert r.headers.get("X-Frame-Options") == "DENY", url
        assert "frame-ancestors 'none'" in r.headers.get("Content-Security-Policy", ""), url


# --------------------------------------------------------------------------- #
# VULN-6  Stored XSS (CWE-79)
# --------------------------------------------------------------------------- #
def test_comment_script_is_escaped(app, client):
    login(client, "bob")
    post = post_by_title(app, "Welcome to the Robotics Society blog")
    post_form(client, f"/post/{post.id}", f"/post/{post.id}/comment", {"body": "<script>alert('xss')</script>"})
    html = client.get(f"/post/{post.id}").get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in html


def test_post_body_html_is_sanitized(app, client):
    login(client, "alice")
    body = 'Hi <img src=x onerror="alert(1)"> <script>alert(2)</script>'
    post_form(client, "/write", "/write", {"title": "XSS body", "body": body, "publish": "on"})
    post = post_by_title(app, "XSS body")
    html = client.get(f"/post/{post.id}").get_data(as_text=True)
    assert "onerror" not in html
    assert "<script>alert(2)</script>" not in html


# --------------------------------------------------------------------------- #
# VULN-7  Insecure configuration
# --------------------------------------------------------------------------- #
def test_secret_key_is_not_hardcoded(app):
    assert app.config["SECRET_KEY"] != "inkpost-dev-secret"
    assert len(app.config["SECRET_KEY"]) >= 32


def test_debug_mode_not_enabled_in_entrypoint():
    with open(os.path.join(os.path.dirname(__file__), "..", "run.py"), encoding="utf-8") as f:
        assert "debug=True" not in f.read()


def test_login_is_rate_limited(client):
    statuses = [
        post_form(client, "/login", "/login", {"username": "alice", "password": "wrong"}).status_code
        for _ in range(8)
    ]
    assert 429 in statuses
