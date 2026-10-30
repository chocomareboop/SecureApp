"""Development entry point: python run.py"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("INKPOST_HOST", "127.0.0.1")
    # FIX-7 (CWE-489): debug is opt-in via FLASK_DEBUG=1 and never used in Docker.
    app.run(host=host, port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
