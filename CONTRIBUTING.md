# Contributing to Trustra Flight Recorder

Thanks for considering a contribution. This project is AGPL-3.0-or-later, so any modified version run as a network service must make its source available to its users; contributing changes back upstream is the simplest way to comply and benefits everyone.

## Ground rules

- Open an issue before starting significant work.
- Keep pull requests focused; smaller, single-purpose PRs are reviewed faster.
- Add or update tests for any behavior change, especially anything touching `provenance.py` or `export.py`, since correctness there is the entire point of this project.
- New redactors should implement the `Redactor` interface in `redaction.py` and include a unit test.

## Development setup

```bash
git clone <this repository>
cd trustra-flight-recorder
pip install -e ".[dev]"
pytest
```

## Reporting issues

Please include: what you expected, what happened, a minimal reproduction if possible, and your environment (Python version, OS).

## Security issues

Do not open a public issue for a security vulnerability. See `SECURITY.md` for a private contact.

## Scope note

Pull requests that add attestation, certification, compliance sign-off, or claims of independent verification will not be accepted into this repository. That is intentionally a separate, accountable layer outside this codebase. This project stays focused on tamper-evident capture and export of what an agent did, nothing more.

## Code of conduct

Be respectful, assume good faith, and keep disagreements about code, not people.
