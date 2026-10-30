import os
import re
import struct
import subprocess

import pytest

from app import create_app
from app.models import Post, User

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE_DIR = os.path.join(ROOT, "native")
NATIVE_LIB = os.path.join(NATIVE_DIR, "build", "libinkparser.so")
NATIVE_CLI = os.path.join(NATIVE_DIR, "build", "ink_parser_cli")

# Smallest valid PNG (1x1 transparent pixel).
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)

PASSWORDS = {"admin": "admin-pass-123", "alice": "alice-pass-123", "bob": "bob-pass-123"}


@pytest.fixture(scope="session", autouse=True)
def build_native():
    subprocess.run(["make", "-C", NATIVE_DIR, "lib", "cli"], check=True, capture_output=True)


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.db"),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
            "NATIVE_LIB": NATIVE_LIB,
        }
    )
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_token(client, url):
    """Return the CSRF token rendered on a page, or None if the page has none."""
    html = client.get(url).get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


def post_form(client, page_url, action_url, data=None, **kwargs):
    """Submit a form the way a real browser would: include the page's CSRF token if it has one."""
    data = dict(data or {})
    token = csrf_token(client, page_url)
    if token:
        data["csrf_token"] = token
    return client.post(action_url, data=data, **kwargs)


def login(client, username):
    return post_form(client, "/login", "/login", {"username": username, "password": PASSWORDS[username]})


def user_id(app, username):
    with app.app_context():
        return User.query.filter_by(username=username).one().id


def post_by_title(app, title):
    with app.app_context():
        return Post.query.filter_by(title=title).one_or_none()


def make_ink(title: bytes, tags: bytes = b"", body: bytes = b"Hello from an imported file."):
    return b"INK1" + struct.pack("<H", len(title)) + title + struct.pack("<H", len(tags)) + tags + body
