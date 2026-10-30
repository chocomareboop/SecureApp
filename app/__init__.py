"""InkPost — a mini blog for university societies.

Hardened build. The original lab vulnerabilities are preserved at the git tag
v0-vulnerable; each fix is marked FIX-n in the code.
"""
import os
import secrets

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from .models import db
from .seed import register_cli, seed_if_empty

csrf = CSRFProtect()

# FIX-5 (CWE-1021) + defense in depth for XSS: strict CSP. Pages never load
# inline scripts, so script-src can stay 'self'.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_secret_key(instance_path):
    """FIX-7 (CWE-798): secret from the environment, or a random key generated
    once and stored in the instance folder with owner-only permissions."""
    env_key = os.environ.get("INKPOST_SECRET_KEY")
    if env_key:
        return env_key
    key_file = os.path.join(instance_path, "secret_key")
    if os.path.exists(key_file):
        with open(key_file, encoding="utf-8") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    try:
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:  # another worker created it first
        with open(key_file, encoding="utf-8") as f:
            return f.read().strip()
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key)
    return key


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=_load_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "inkpost.db"),
        UPLOAD_DIR=os.path.join(app.instance_path, "uploads"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # FIX-2: cap upload size at 5 MB
        # FIX-4 (CWE-352): hardened session cookie. Secure is enabled whenever the
        # app is served over HTTPS (set INKPOST_SECURE_COOKIES=1 in production).
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("INKPOST_SECURE_COOKIES", "0") == "1",
        WTF_CSRF_TIME_LIMIT=3600,
        NATIVE_LIB=os.environ.get(
            "INKPOST_NATIVE_LIB", os.path.join(BASE_DIR, "native", "build", "libinkparser.so")
        ),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)  # FIX-4: synchronizer token required on every POST

    from .filters import register_filters
    from .routes import bp

    register_filters(app)
    app.register_blueprint(bp)
    register_cli(app)

    # FIX-7: throttle login attempts (credential stuffing / brute force).
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    limiter.init_app(app)
    app.view_functions["main.login"] = limiter.limit("5 per minute", methods=["POST"])(
        app.view_functions["main.login"]
    )

    @app.after_request
    def set_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    with app.app_context():
        db.create_all()
        seed_if_empty()

    return app
