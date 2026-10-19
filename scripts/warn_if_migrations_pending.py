from __future__ import annotations

import re
import subprocess
import sys


def _run_alembic(*args: str) -> tuple[int, str]:
    process = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
    )
    output = (process.stdout or "") + (process.stderr or "")
    return process.returncode, output


def _extract_revisions(output: str) -> set[str]:
    revisions: set[str] = set()
    for line in output.splitlines():
        match = re.match(r"^([0-9a-f]{8,})\b", line.strip())
        if match:
            revisions.add(match.group(1))
    return revisions


def _warn(message: str) -> None:
    print(f"WARNING: {message}")
    print("Run `python -m alembic upgrade head` for the current environment if needed.")


def _ok(message: str) -> None:
    print(f"Schema check: {message}")


def main() -> int:
    current_code, current_output = _run_alembic("current")
    if current_code != 0:
        _warn(
            "Could not verify migration status (database may be unavailable or DATABASE_URL may be unset)."
        )
        return 0

    head_code, heads_output = _run_alembic("heads")
    if head_code != 0:
        _warn("Could not read Alembic head revisions.")
        return 0

    current_revisions = _extract_revisions(current_output)
    head_revisions = _extract_revisions(heads_output)

    if not current_revisions:
        _warn(
            "No Alembic revision is recorded for this database (alembic_version is missing or empty)."
        )
        return 0

    if not head_revisions:
        _ok("migration revisions loaded, but no Alembic heads were reported.")
        return 0

    if not head_revisions.issubset(current_revisions):
        _warn("Pending database migrations detected.")
        return 0

    if current_revisions == head_revisions:
        revision = sorted(current_revisions)[0]
        _ok(f"no Alembic migrations due (current=head={revision}).")
    else:
        _ok("no Alembic migrations due (database is at all head revisions).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
