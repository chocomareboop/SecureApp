# Security Policy

## Scope

InkPost is a teaching application for CYC386. The `v0-vulnerable` tag intentionally contains the
vulnerabilities listed in the README; `main` is the hardened version.

## Supported versions

| Version | Supported |
|---|---|
| `main` (hardened) | ✅ |
| `v0-vulnerable` | ❌ lab demonstration only |

## Reporting a vulnerability

Open a **private** report through GitHub → *Security* → *Report a vulnerability*, or email a team maintainer.
Please include steps to reproduce, affected endpoint or file, and impact. We aim to acknowledge reports within 48 hours.
Do not open public issues for unfixed vulnerabilities.

## Security controls on `main`

- **Authorization:** every post access goes through `app/authz.py` (object-level checks).
- **CSRF:** synchronizer tokens on every state-changing request; session cookie `HttpOnly`, `SameSite=Lax`, `Secure` outside localhost.
- **Framing / XSS:** `X-Frame-Options: DENY`, strict Content-Security-Policy, autoescaping, bleach-sanitized Markdown.
- **Command execution:** no shell; fixed argument vectors; server-generated upload names; magic-byte validation.
- **Native code:** length fields validated against destination and input size; built with
  `-fstack-protector-strong -D_FORTIFY_SOURCE=2`, full RELRO, NX, PIE; ASAN in CI.
- **Configuration:** secret key from the environment, debug disabled, login rate limiting.
- **Pipeline:** tests, Bandit, Semgrep, CodeQL, OWASP ZAP and Trivy run on every push and pull request; HIGH/CRITICAL findings fail the build.

## Ethics

All exploitation is limited to systems the team controls. PoC scripts refuse non-localhost targets.
