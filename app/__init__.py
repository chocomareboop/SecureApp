"""InkPost — a mini blog for university societies.

LAB BUILD: this baseline intentionally contains vulnerabilities (marked VULN-n)
for the CYC386 DevSecOps sprint. Run it only on 127.0.0.1.
"""
import os

from flask import Flask

from .models import db
from .seed import register_cli, seed_if_empty

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        # VULN-7 (CWE-798): hardcoded, guessable session-signing key.
        SECRET_KEY="inkpost-dev-secret",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "inkpost.db"),
        UPLOAD_DIR=os.path.join(app.instance_path, "uploads"),
        NATIVE_LIB=os.environ.get(
            "INKPOST_NATIVE_LIB", os.path.join(BASE_DIR, "native", "build", "libinkparser.so")
        ),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    db.init_app(app)

    from .filters import register_filters
    from .routes import bp

    register_filters(app)
    app.register_blueprint(bp)
    register_cli(app)

    with app.app_context():
        db.create_all()
        seed_if_empty()

    return app
