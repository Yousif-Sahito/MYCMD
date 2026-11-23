"""Inspect packaged GUI modules/assets and run existing isolated wheel checks."""

import subprocess
import sys
import zipfile
from pathlib import Path


def main() -> None:
    wheel = Path(sys.argv[1]).resolve()
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for name in ("mycmd/gui/__init__.py", "mycmd/gui/app.py"):
            if name not in names:
                raise RuntimeError(f"Missing GUI module: {name}")
        for suffix in (".html", ".js", ".css"):
            if not any(name.startswith("mycmd/gui/") and name.endswith(suffix) for name in names):
                raise RuntimeError(f"Missing bundled terminal renderer asset: {suffix}")
        if not any("license" in name.lower() for name in names if name.startswith("mycmd/gui/")):
            raise RuntimeError("Missing bundled renderer license")
        if not any(name.endswith("entry_points.txt") for name in names):
            raise RuntimeError("Missing installed launcher entry points")
        print("Packaged GUI, renderer asset types, license and launcher metadata found")
    subprocess.run([sys.executable, "scripts/check_wheel.py", str(wheel)], check=True)


if __name__ == "__main__":
    main()
