"""InkPost — a mini blog for university societies.

LAB BUILD: this baseline intentionally contains vulnerabilities (marked VULN-n)
for the CYC386 DevSecOps sprint. Run it only on 127.0.0.1.
"""
import os

from flask import Flask
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


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        # VULN-7 (CWE-798): hardcoded, guessable session-signing key.
        SECRET_KEY="inkpost-dev-secret",
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

    @app.after_request
    def set_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    with app.app_context():
        db.create_all()
        seed_if_empty()

    return app
