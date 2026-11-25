"""Build and validate an OS-specific PyInstaller desktop executable."""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (root / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = root / ".tools" / "phase9-pyinstaller"
    work.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(output),
        "--workpath",
        str(work),
        str(root / "MYCMD_GUI.spec"),
    ]
    subprocess.run(command, cwd=root, check=True)
    expected = output / ("MYCMD.exe" if sys.platform == "win32" else "MYCMD")
    if not expected.is_file():
        raise RuntimeError(f"Missing packaged executable: {expected}")
    print(f"Built packaged GUI executable: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
