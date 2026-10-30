# Contributing

## Branches

| Branch | Purpose |
|---|---|
| `main` | Protected. No direct pushes. Changes land only through reviewed pull requests. |
| `develop` | Optional integration branch. |
| `feature/<jira-key>-short-name` | New functionality, e.g. `feature/SAS-8-markdown-preview` |
| `fix/<jira-key>-short-name` | Security fixes, e.g. `fix/SAS-14-idor-posts` |

## Pull requests

1. Branch from `main`, keep each PR focused on one fix or feature.
2. Title: `SAS-<n>: <what changed>`; link the Jira issue and the threat ID (e.g. `VULN-3 / STRIDE-E2`).
3. Include before/after evidence (test output, screenshots) for security fixes.
4. At least **one teammate must review and approve**. The author never approves their own PR.
5. CI must be green before merging (required status checks are enabled once the baseline fixes are in).

## Commits

Use `SAS-<n>: imperative summary`, for example:

```
SAS-14: enforce object-level authorization on post routes
```

Jira's GitHub integration links commits and PRs that mention the issue key.

## Local checks before pushing

```bash
make -C native
pytest -v
bandit -r app run.py wsgi.py --severity-level high
```

## Secure coding checklist

- [ ] Every object access checks ownership/role (`authorize()`).
- [ ] No `shell=True`, no string-built commands.
- [ ] All user input validated (type, length, allow-list).
- [ ] Forms include `csrf_token`.
- [ ] No `|safe` on user content.
- [ ] Native code never trusts length/size fields from input.
- [ ] No secrets in code; config comes from the environment.
