import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from mycmd.core.service import Service
from mycmd.storage.database import connect


def test_10k_project_list_completes_within_target(tmp_path: Path) -> None:
    db = connect(tmp_path / "performance.sqlite3")
    service = Service(db, str(uuid4()))
    stamp = "2026-11-25T18:51:57Z"
    rows = [
        (
            str(uuid4()),
            service.owner_id,
            "projects",
            json.dumps(
                {
                    "slug": f"project-{index}",
                    "title": f"Project {index}",
                    "status": "active",
                },
                separators=(",", ":"),
            ),
            stamp,
            stamp,
            1,
            None,
            "pending",
            0,
        )
        for index in range(10_000)
    ]
    db.executemany(
        "INSERT INTO records("
        "id,owner_id,kind,data,created_at,updated_at,version,"
        "deleted_at,sync_status,last_server_version"
        ") VALUES(?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    db.commit()

    start = time.perf_counter()
    records = service.list("projects")
    elapsed = time.perf_counter() - start

    assert len(records) == 10_000
    assert elapsed < 0.250, f"10,000-record list took {elapsed:.3f}s"
    db.close()


def test_cli_help_cold_start_within_target(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["MYCMD_DATA_DIR"] = str(tmp_path)
    env["NO_COLOR"] = "1"
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "mycmd", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    assert result.returncode == 0
    assert elapsed < 2.0, f"CLI cold start took {elapsed:.3f}s"
