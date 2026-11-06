# Security Policy

## Supported Versions

Jigsaurium is currently pre-release. Security fixes are provided for:

- `main` (latest commit)
- The most recent release tag (once public releases begin)

Older versions may not receive security updates.

## Reporting a Vulnerability

Please **do not** report security vulnerabilities in public issues.

Use one of the following private channels:

1. **GitHub Private Vulnerability Reporting** (preferred once repository is public)
2. Contact maintainers directly (as documented in project governance/contact files)

Maintainer contact path is documented in `GOVERNANCE.md`.

If neither private channel is available, open a minimal issue asking maintainers for a private contact path without sharing exploit details.

Include, where possible:

- Affected component/endpoint
- Reproduction steps or proof of concept
- Impact assessment (confidentiality/integrity/availability)
- Suggested remediation (if known)

## Response Expectations

- Initial acknowledgement: **within 3 business days**
- Triage and severity assessment: **within 14 calendar days**
- Remediation target:
  - Critical/High: as quickly as possible, target **<= 30 days**
  - Medium/Low: scheduled into normal release planning

Timelines may vary based on complexity and release windows, but maintainers will provide status updates during handling.

## Disclosure Policy

- Please allow time for validation and remediation before public disclosure.
- After a fix is released, maintainers may publish an advisory/changelog note with impact and mitigation details.

## Security Hygiene Notes

- Do not commit secrets (`*.local` env files are intentionally git-ignored).
- Use environment variables for credentials and API keys.
- Follow the operational/security guidance in `Documentation/operations-and-security.md`.
