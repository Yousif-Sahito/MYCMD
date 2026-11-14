"""Run the dependency-free subset of Phase 0 checks; not a substitute for CI."""

import compileall
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests" / "unit"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    compiled = all(
        compileall.compile_dir(str(ROOT / folder), quiet=1) for folder in ("src", "server", "tests")
    )
    print(f"Python compilation: {compiled}")
    print("Full pytest, lint, format, typecheck, lock and build gates remain separate.")
    return 0 if result.wasSuccessful() and compiled else 1


if __name__ == "__main__":
    raise SystemExit(main())
