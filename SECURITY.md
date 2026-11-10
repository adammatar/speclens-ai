# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| `main` (latest) | Yes |
| Older tags / forks | Best-effort only |

## Reporting a vulnerability

Please report security issues **privately** — do not open a public GitHub issue for exploitable findings.

1. Email the repository owner (Adam Matar) using the contact listed on [mataradam.com](https://mataradam.com) / the GitHub profile.
2. Include a clear description, impact, and steps to reproduce with **synthetic** data only.
3. Allow a reasonable window for triage before public disclosure.

## Expectations

- Demo and evaluation content in this repository is **synthetic**. Do not upload or attach confidential customer specifications when reporting issues.
- Local bootstrap credentials (`speclens-local-dev-key`, `speclens_dev_password`) are for local/CI only and must never be used on public deployments.
- Secrets (API keys, provider tokens, `.env`) must not be committed.

## Preferred disclosure

Responsible disclosure with coordinated fix and credit (if desired) is welcome. Please avoid testing against deployments you do not operate.
