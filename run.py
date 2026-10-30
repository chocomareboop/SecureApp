"""Development entry point: python run.py"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("INKPOST_HOST", "127.0.0.1")
    # VULN-7 (CWE-489): debug mode exposes the interactive Werkzeug debugger.
    app.run(host=host, port=5000, debug=True)
