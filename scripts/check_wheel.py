"""Smoke-test an extracted wheel in isolated Python, without the source checkout."""

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SMOKE = """
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0, sys.argv[1])
import mycmd
from mycmd.storage.database import connect
from mycmd.core.service import Service
assert Path(mycmd.__file__).is_relative_to(Path(sys.argv[1]))
path = Path(sys.argv[1]) / 'smoke.db'
owner = str(uuid4())
db = connect(path)
service = Service(db, owner)
record = service.create('projects', {'slug':'wheel', 'title':'Wheel', 'status':'active'})
db.close()
db = connect(path)
service = Service(db, owner)
assert service.get(record.id) == record
assert len(service.pending()) == 1
db.close()
print('Wheel import, packaged migration, CRUD, outbox and restart smoke passed')
"""


def main() -> None:
    wheel = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="mycmd-wheel-") as directory:
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert "mycmd/storage/migrations/001_initial.sql" in names
            for name in (
                "mycmd/terminal/session.py",
                "mycmd/terminal/windows.py",
                "mycmd/terminal/posix.py",
            ):
                assert name in names, f"Missing terminal engine module: {name}"
            assert not any(name.startswith(("server/", "tests/", "apps/")) for name in names)
            for name in names:
                destination = (Path(directory) / name).resolve()
                if not destination.is_relative_to(Path(directory).resolve()):
                    raise ValueError("Unsafe wheel member")
            archive.extractall(directory)
        subprocess.run([sys.executable, "-I", "-c", SMOKE, directory], cwd=directory, check=True)


if __name__ == "__main__":
    main()
