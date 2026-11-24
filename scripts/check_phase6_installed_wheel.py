"""Install the server wheel into a clean environment and verify API imports/routes."""

import argparse
import glob
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", nargs="?", default="")
    args = parser.parse_args()
    wheel = args.wheel or (glob.glob(".tools/phase6-dist-final/*.whl")[0])
    root = pathlib.Path(tempfile.mkdtemp(prefix="phase6-wheel"))
    venv = root / "venv"
    try:
        subprocess.run(["uv", "venv", "--python", sys.executable, str(venv)], check=True)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), f"{wheel}[server]"],
            check=True,
        )
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["DATABASE_URL"] = "sqlite+pysqlite:///" + str(root / "api.sqlite3").replace("\\", "/")
        env["MYCMD_SECRET_KEY"] = "installed-api-test-signing-key-at-least-32"
        env["MYCMD_BOOTSTRAP_TOKEN"] = "installed-api-bootstrap-token"
        code = (
            "from server.app.main import app;"
            "from fastapi.routing import APIRoute;"
            "print(app.title);"
            "paths={r.path for r in app.routes if isinstance(r, APIRoute)};"
            "print('/health' in paths);"
            "print('/api/v1/public/portfolio' in paths)"
        )
        result = subprocess.run(
            [str(python), "-I", "-c", code],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        if "MYCMD API" not in result.stdout or "True" not in result.stdout:
            raise RuntimeError("Installed API smoke did not expose expected routes")
        print("Clean installed Phase 6 server wheel import and routes passed")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
