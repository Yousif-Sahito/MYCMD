import json
from pathlib import Path
from uuid import uuid4

import pytest

from mycmd.api_client.client import ApiClient
from mycmd.core.service import Service
from mycmd.storage.database import connect
from mycmd.sync.coordinator import SyncCoordinator


class StubClient(ApiClient):
    def __init__(self) -> None:
        pass

    def push(self, operations):  # type: ignore[no-untyped-def]
        raise AssertionError("Not used")

    def pull(self, cursor: int, limit: int = 100):  # type: ignore[no-untyped-def]
        raise AssertionError("Not used")


def service(tmp_path: Path) -> tuple[Service, object]:
    db = connect(tmp_path / "sync.sqlite3")
    return Service(db, str(uuid4())), db


def add_conflict(tmp_path: Path) -> tuple[SyncCoordinator, str]:
    local, db = service(tmp_path)
    record = local.create(
        "projects",
        {
            "slug": "merge-project",
            "title": "Local title",
            "status": "active",
            "technologies": [],
            "links": [],
        },
    )
    conflict_id = str(uuid4())
    db.execute(
        "INSERT INTO local_conflicts("
        "id,owner_id,entity_type,entity_id,local_json,server_json,"
        "local_version,server_version,conflict_type,state,created_at,resolved_at"
        ") VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)",
        (
            conflict_id,
            local.owner_id,
            "projects",
            record.id,
            json.dumps({"version": record.version, "data": record.data}),
            json.dumps(
                {
                    "id": record.id,
                    "kind": "projects",
                    "data": {
                        "slug": "merge-project",
                        "title": "Server title",
                        "status": "active",
                        "technologies": [],
                        "links": [],
                    },
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                    "version": 2,
                    "deleted_at": None,
                }
            ),
            record.version,
            2,
            "optimistic_version",
            "pending",
            record.updated_at,
        ),
    )
    db.commit()
    return SyncCoordinator(local, StubClient()), conflict_id


def test_manual_merge_validates_domain(tmp_path: Path) -> None:
    coordinator, conflict_id = add_conflict(tmp_path)
    with pytest.raises(ValueError):
        coordinator.resolve_manual_merge(
            conflict_id,
            {"slug": "INVALID SLUG", "title": "Merged", "status": "active"},
        )
    assert coordinator._conflict_row(conflict_id)["state"] == "pending"


def test_manual_merge_queues_version_checked_update(tmp_path: Path) -> None:
    coordinator, conflict_id = add_conflict(tmp_path)
    result = coordinator.resolve_manual_merge(
        conflict_id,
        {
            "slug": "merge-project",
            "title": "Merged title",
            "status": "completed",
            "technologies": ["Python"],
            "links": [],
        },
    )
    assert result["status"] == "queued"
    assert result["resolution"] == "manual_merge"
    row = coordinator.service.db.execute(
        "SELECT state FROM local_conflicts WHERE id=?",
        (conflict_id,),
    ).fetchone()
    assert row["state"] == "resolution_pending"
    queued = coordinator.service.pending()
    assert len(queued) == 2
    assert queued[-1]["action"] == "update"
    assert queued[-1]["base_version"] == 2


def test_keep_server_is_explicit(tmp_path: Path) -> None:
    coordinator, conflict_id = add_conflict(tmp_path)
    result = coordinator.resolve_keep_server(conflict_id)
    assert result == {"status": "resolved", "resolution": "keep_server"}
    conflict = coordinator.service.db.execute(
        "SELECT entity_id,state FROM local_conflicts WHERE id=?",
        (conflict_id,),
    ).fetchone()
    assert conflict["state"] == "resolved_keep_server"
    record = coordinator.service.get(conflict["entity_id"])
    assert record.data["title"] == "Server title"
