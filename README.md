# InkPost — SecureApp-Sprint

A mini blog for university societies, built for the **CYC386 Secure Software Design & Development** DevSecOps sprint.
Members write Markdown stories with cover images, import `.ink` files through a native C parser, and comment on each other's posts.

> ⚠️ **Lab software.** The `v0-vulnerable` tag deliberately contains vulnerabilities for demonstration.
> Run it **only on 127.0.0.1** and never expose it to a network.

## Architecture

| Component | Tech | Notes |
|---|---|---|
| Web app | Python 3.12, Flask, Jinja2 | `app/` — routes, templates, CSS/JS (no inline scripts, CSP-ready) |
| Database | SQLite via Flask-SQLAlchemy | `instance/inkpost.db`, auto-seeded |
| Native parser | C (`native/ink_parser.c`) | Loaded with `ctypes`; also built as a standalone CLI for demos |
| File inspector | `file(1)` via `subprocess` | Cover image type check |
| CI/CD | GitHub Actions | Tests, Bandit, Semgrep, CodeQL, OWASP ZAP, Trivy |

## Run it

### Option A — Docker (recommended, works on Windows/macOS/Linux)

```bash
docker compose up --build
```
Open <http://localhost:5000>.

### Option B — Linux / WSL / macOS

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
make -C native            # builds native/build/libinkparser.so and the CLI
python run.py             # http://127.0.0.1:5000
```
> The native parser and `file` command need Linux or macOS. On Windows use Docker or WSL.

### Demo accounts

| User | Password | Role |
|---|---|---|
| `admin` | `admin-pass-123` | admin (id 1) |
| `alice` | `alice-pass-123` | member (id 2) — owns a confidential draft |
| `bob` | `bob-pass-123` | member (id 3) — plays the attacker |

Reset the data at any time: `flask --app app seed --reset`

## Test

```bash
make -C native
pytest -v
```

* `tests/test_features.py` — functionality; passes on every commit.
* `tests/test_security.py` — one block per threat in the risk register. **Fails on `v0-vulnerable`, passes once all fixes are merged.**

Native hardening evidence:

```bash
make -C native hardening-report   # stack canary, FORTIFY, NX, RELRO, PIE
make -C native asan && ./native/build/ink_parser_cli_asan poc/out/bof_crash.ink
```

## Vulnerabilities and fixes

| ID | Class | CWE | Where | Fix |
|---|---|---|---|---|
| VULN-1 | Buffer overflow | CWE-120 | `native/ink_parser.c` trusts the title length field | Bounds checks + hardened build flags; Python no longer trusts parser ownership |
| VULN-2 | OS command injection | CWE-78 | Cover inspector runs `file {name}` with `shell=True` | Argument list, `shell=False`, UUID filenames, magic-byte check |
| VULN-3 | IDOR | CWE-639 | Edit/delete/publish/API look posts up by ID only | Central `authorize()` on every access |
| VULN-4 | CSRF | CWE-352 | No tokens on state-changing forms | Flask-WTF synchronizer tokens + `SameSite=Lax` |
| VULN-5 | Clickjacking | CWE-1021 | No framing protection | `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` |
| VULN-6 | Stored XSS | CWE-79 | Comments and Markdown rendered unescaped | Autoescape + bleach sanitizer + CSP |
| VULN-7 | Insecure config | CWE-798 / CWE-489 | Hardcoded secret, debug mode, no login throttling | Env secret, gunicorn, Flask-Limiter |

Proof-of-concept scripts live in `poc/` (see the header of each file). They refuse to target anything but localhost.

## Repository workflow

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching, PR review and commit conventions, and [SECURITY.md](SECURITY.md) for the security policy.
