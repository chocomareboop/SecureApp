"""Functional tests: the app must keep working after every security fix."""
import io

from app.models import Post

from .conftest import PNG_1X1, login, make_ink, post_by_title, post_form, user_id


def test_feed_shows_only_published(client):
    html = client.get("/").get_data(as_text=True)
    assert "Welcome to the Robotics Society blog" in html
    assert "Budget 2026" not in html


def test_login_and_logout(client):
    r = login(client, "alice")
    assert r.status_code == 302
    assert "Log out" in client.get("/").get_data(as_text=True)
    post_form(client, "/", "/logout")
    assert "Log in" in client.get("/").get_data(as_text=True)


def test_wrong_password_rejected(client):
    r = post_form(client, "/login", "/login", {"username": "alice", "password": "nope"})
    assert r.status_code == 200
    assert "Incorrect username or password" in r.get_data(as_text=True)


def test_owner_can_write_and_edit(app, client):
    login(client, "alice")
    r = post_form(client, "/write", "/write", {"title": "My new story", "body": "Body text", "tags": "x", "publish": "on"})
    assert r.status_code == 302
    post = post_by_title(app, "My new story")
    assert post is not None and post.is_published
    r = post_form(client, f"/post/{post.id}/edit", f"/post/{post.id}/edit", {"title": "Edited story", "body": "New body"})
    assert r.status_code == 302
    assert post_by_title(app, "Edited story") is not None


def test_owner_can_view_own_draft(app, client):
    login(client, "alice")
    draft = post_by_title(app, "Budget 2026 — confidential draft")
    assert client.get(f"/post/{draft.id}").status_code == 200
    assert client.get(f"/api/posts/{draft.id}").status_code == 200


def test_owner_can_delete(app, client):
    login(client, "bob")
    post = post_by_title(app, "Draft: elections timeline")
    r = post_form(client, f"/post/{post.id}", f"/post/{post.id}/delete")
    assert r.status_code == 302
    assert post_by_title(app, "Draft: elections timeline") is None


def test_cover_upload_and_inspect(app, client):
    login(client, "alice")
    data = {"title": "Cover test", "body": "b", "cover": (io.BytesIO(PNG_1X1), "photo.png")}
    r = post_form(client, "/write", "/write", data, content_type="multipart/form-data")
    assert r.status_code == 302
    post = post_by_title(app, "Cover test")
    assert post.cover_filename
    r = post_form(client, f"/post/{post.id}/edit", f"/post/{post.id}/cover-info")
    assert r.status_code == 200
    assert "PNG" in r.get_data(as_text=True) or "image/png" in r.get_data(as_text=True)


def test_valid_ink_import_creates_own_draft(app, client):
    login(client, "bob")
    data = {"ink_file": (io.BytesIO(make_ink(b"Imported notes", b"import")), "notes.ink")}
    r = post_form(client, "/import", "/import", data, content_type="multipart/form-data")
    assert r.status_code == 302
    post = post_by_title(app, "Imported notes")
    assert post is not None
    assert post.author_id == user_id(app, "bob")
    assert post.is_published is False


def test_comment_on_published_post(app, client):
    login(client, "bob")
    post = post_by_title(app, "Welcome to the Robotics Society blog")
    r = post_form(client, f"/post/{post.id}", f"/post/{post.id}/comment", {"body": "Great post"})
    assert r.status_code == 302
    assert "Great post" in client.get(f"/post/{post.id}").get_data(as_text=True)


def test_email_change_with_form(app, client):
    login(client, "alice")
    r = post_form(client, "/settings", "/settings/email", {"email": "alice2@inkpost.local"})
    assert r.status_code == 302
    with app.app_context():
        assert Post.query.count() >= 1
    assert "alice2@inkpost.local" in client.get("/settings").get_data(as_text=True)


def test_admin_page_requires_admin(client):
    login(client, "bob")
    assert client.get("/admin").status_code == 403
