"""Install the desktop wheel into a fresh environment and execute its GUI harness."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--uv", default=shutil.which("uv") or "uv")
    parser.add_argument(
        "--smoke-script", type=Path, default=Path(__file__).with_name("gui_smoke.py")
    )
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    harness = args.smoke_script.resolve(strict=True)
    if wheel.suffix != ".whl":
        raise ValueError("Expected a built wheel")
    with tempfile.TemporaryDirectory(prefix="mycmd-installed-gui-") as directory:
        root = Path(directory)
        environment = root / "venv"
        subprocess.run(
            [args.uv, "venv", "--python", sys.executable, str(environment)], check=True, timeout=120
        )
        binary = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binary / ("python.exe" if os.name == "nt" else "python")
        launcher = binary / ("mycmd.exe" if os.name == "nt" else "mycmd")
        subprocess.run(
            [args.uv, "pip", "install", "--python", str(python), f"{wheel}[gui]"],
            check=True,
            timeout=300,
        )
        subprocess.run([args.uv, "pip", "check", "--python", str(python)], check=True, timeout=60)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["MYCMD_DATA_DIR"] = str(root / "data")
        for command in (
            [str(launcher), "--help"],
            [str(launcher), "status"],
            [str(python), "-I", str(harness)],
        ):
            subprocess.run(command, cwd=root, env=env, check=True, timeout=120)
        print("Clean installed desktop wheel CLI and GUI harness passed")


if __name__ == "__main__":
    main()
