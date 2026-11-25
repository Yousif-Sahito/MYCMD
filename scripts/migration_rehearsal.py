"""Rehearse migration rollback and forward on a disposable database."""

import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        raise RuntimeError("Migration rehearsal requires --confirm")
    database_url = os.getenv("MYCMD_REHEARSAL_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("MYCMD_REHEARSAL_DATABASE_URL is required")
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    command = [sys.executable, "-m", "alembic", "-c", "alembic.ini"]
    subprocess.run(command + ["downgrade", "base"], env=env, check=True)
    subprocess.run(command + ["upgrade", "head"], env=env, check=True)
    print("Migration rollback and forward rehearsal passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
