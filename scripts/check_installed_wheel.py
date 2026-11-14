"""Install the built wheel into a clean environment and exercise its CLI and PTY."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_installed_wheel.py WHEEL")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv must be available to create the clean wheel environment")
    wheel = Path(sys.argv[1]).resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError(f"Wheel not found: {wheel}")

    with tempfile.TemporaryDirectory(prefix="mycmd-installed-wheel-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        subprocess.run(
            [
                uv,
                "venv",
                "--python",
                f"{sys.version_info.major}.{sys.version_info.minor}",
                str(environment),
            ],
            check=True,
        )
        python = (
            environment / "Scripts" / "python.exe"
            if os.name == "nt"
            else environment / "bin" / "python"
        )
        subprocess.run([uv, "pip", "install", "--python", str(python), str(wheel)], check=True)
        subprocess.run([uv, "pip", "check", "--python", str(python)], check=True)
        executable = (
            environment / "Scripts" / "mycmd.exe"
            if os.name == "nt"
            else environment / "bin" / "mycmd"
        )
        data = root / "data"
        env = os.environ.copy()
        env["MYCMD_DATA_DIR"] = str(data)
        subprocess.run([str(executable), "--help"], cwd=root, env=env, check=True)
        subprocess.run([str(executable), "status"], cwd=root, env=env, check=True)

        smoke = """
import asyncio, os, sys
from pathlib import Path
from mycmd.terminal import TerminalSession, discover_shell

async def read_marker(session, marker):
    output = bytearray()
    async for event in session.read_events():
        if event.error:
            raise RuntimeError(event.error)
        output.extend(event.data)
        if marker.encode() in output:
            return
    raise RuntimeError(f'Shell exited before writing marker: {output!r}')

async def verify():
    root = Path(sys.argv[1])
    windows = os.name == 'nt'
    session = TerminalSession(discover_shell('cmd' if windows else 'bash'), root)
    session.start()
    marker = 'MYCMD-INSTALLED-PTY-MARK'
    try:
        if windows:
            session.write(b'set A=MYCMD-INSTALLED-\\r\\nset B=PTY-MARK\\r\\necho %A%%B%\\r\\n')
        else:
            session.write(b"printf 'MYCMD-INSTALLED-' ; printf 'PTY-MARK\\\\n'\\n")
        await read_marker(session, marker)
    finally:
        session.terminate()

asyncio.run(asyncio.wait_for(verify(), 10))
print('Clean installed wheel CLI and real shell smoke passed')
"""
        subprocess.run(
            [str(python), "-I", "-c", smoke, str(root)],
            cwd=root,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
