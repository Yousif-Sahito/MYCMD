import json
import os
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest

from mycmd.core.backup import export_backup, import_backup
from mycmd.core.models import ValidationError
from mycmd.core.service import ConflictError, NotFoundError, Service
from mycmd.storage.database import connect

EXAMPLES = {
    "projects": {"slug": "my-project", "title": "Project", "status": "active"},
    "skills": {"name": "Python", "category": "Language", "level": "advanced"},
    "education": {"institution": "University", "program": "Computing", "status": "completed"},
    "certificates": {"name": "Certificate", "issuer": "Issuer"},
    "milestones": {"title": "Ship", "priority": "high", "status": "active"},
}


@pytest.fixture
def service(tmp_path):
    db = connect(tmp_path / "data.db")
    yield Service(db, str(uuid4()))
    db.close()


@pytest.mark.parametrize("kind", EXAMPLES)
def test_crud_restart_and_owner_scope(service, tmp_path, kind):
    record = service.create(kind, EXAMPLES[kind])
    updated = service.update(record.id, {"notes": "persistent"}, expected_version=1)
    assert updated.version == 2
    assert updated.created_at == record.created_at
    other = Service(service.db, str(uuid4()))
    with pytest.raises(NotFoundError):
        other.get(record.id)
    assert other.list(kind) == [] and other.pending() == []
    with pytest.raises(ConflictError):
        service.update(record.id, {"notes": "stale"}, expected_version=1)
    reopened_db = connect(tmp_path / "data.db")
    reopened = Service(reopened_db, service.owner_id)
    assert reopened.get(record.id) == updated
    assert reopened.pending() == service.pending()
    assert reopened.device_id == service.device_id
    reopened.delete(record.id, expected_version=2)
    assert reopened.list(kind) == []
    assert reopened.get(record.id, include_deleted=True).deleted_at
    assert [op["action"] for op in reopened.pending()] == ["create", "update", "delete"]
    assert len({op["operation_id"] for op in reopened.pending()}) == 3
    reopened_db.close()


def test_outbox_failure_rolls_back_record_and_version(service):
    record = service.create("projects", EXAMPLES["projects"])
    service.db.execute(
        "CREATE TRIGGER fail_outbox BEFORE INSERT ON local_outbox "
        "BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
    )
    with pytest.raises(ConflictError):
        service.update(record.id, {"notes": "must roll back"}, expected_version=1)
    assert service.get(record.id) == record
    assert len(service.pending()) == 1
    with pytest.raises(ConflictError):
        service.create("skills", EXAMPLES["skills"])
    assert service.list("skills") == []


def test_unique_constraints(service):
    service.create("projects", EXAMPLES["projects"])
    with pytest.raises(ConflictError):
        service.create("projects", EXAMPLES["projects"])
    assert len(service.pending()) == 1


def test_backup_roundtrip_dry_run_and_corruption(service, tmp_path):
    for kind, data in EXAMPLES.items():
        service.create(kind, data)
    path = tmp_path / "backup.json"
    export_backup(service, path)
    target_db = connect(tmp_path / "restore.db")
    target = Service(target_db, service.owner_id)
    assert import_backup(target, path)["additions"] == 5
    assert target.pending() == []
    assert import_backup(target, path, dry_run=False)["additions"] == 5
    for kind in EXAMPLES:
        assert target.list(kind) == service.list(kind)
    assert import_backup(target, path, dry_run=False)["unchanged"] == 5
    assert len(target.pending()) == 5
    record = target.list("projects")[0]
    target.update(record.id, {"notes": "local edit"}, expected_version=1)
    assert import_backup(target, path, dry_run=False)["conflicts"] == 1
    assert target.get(record.id).data["notes"] == "local edit"
    body = json.loads(path.read_text())
    body["owner_id"] = str(uuid4())
    path.write_text(json.dumps(body))
    with pytest.raises(ValidationError):
        import_backup(target, path)
    target_db.close()


def test_future_and_corrupt_database_preserved(tmp_path):
    path = tmp_path / "future.db"
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version=999")
    db.close()
    with pytest.raises(RuntimeError, match="Unsupported"):
        connect(path)
    bad = tmp_path / "corrupt.db"
    bad.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        connect(bad)
    assert bad.read_bytes() == b"not a database"


def test_process_exit_rolls_back_uncommitted_mutation(service, tmp_path):
    record = service.create("projects", EXAMPLES["projects"])
    script = """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.execute('BEGIN IMMEDIATE')
db.execute("UPDATE records SET version=99")
db.execute("DELETE FROM local_outbox")
os._exit(17)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "data.db")],
        env=os.environ.copy(),
        check=False,
    )
    assert result.returncode == 17
    assert service.get(record.id) == record
    assert len(service.pending()) == 1


def test_invalid_backup_record_cannot_partially_restore(service, tmp_path):
    from mycmd.core.backup import checksum

    service.create("projects", EXAMPLES["projects"])
    service.create("skills", EXAMPLES["skills"])
    path = tmp_path / "backup.json"
    export_backup(service, path)
    body = json.loads(path.read_text())
    body.pop("checksum")
    body["records"]["skills"][0]["data"]["level"] = "invented"
    body["checksum"] = checksum(body)
    path.write_text(json.dumps(body))
    db = connect(tmp_path / "target.db")
    target = Service(db, service.owner_id)
    assert import_backup(target, path, dry_run=False)["invalid"] == 1
    assert target.list("projects") == []
    assert target.pending() == []
    db.close()


@pytest.mark.parametrize("version", [True, 1.0, 2, 0])
def test_invalid_expected_revision_does_not_mutate(service, version):
    record = service.create("projects", EXAMPLES["projects"])
    with pytest.raises(ConflictError):
        service.update(record.id, {"notes": "bad"}, expected_version=version)
    with pytest.raises(ConflictError):
        service.delete(record.id, expected_version=version)
    assert service.get(record.id) == record
    assert len(service.pending()) == 1


def test_export_uses_one_snapshot(service, tmp_path, monkeypatch):
    service.create("projects", EXAMPLES["projects"])
    writer_db = connect(tmp_path / "data.db")
    writer = Service(writer_db, service.owner_id)
    original = service.list

    def concurrent_list(kind, **kwargs):
        rows = original(kind, **kwargs)
        if kind == "projects":
            writer.create("skills", EXAMPLES["skills"])
        return rows

    monkeypatch.setattr(service, "list", concurrent_list)
    path = tmp_path / "snapshot.json"
    export_backup(service, path)
    assert json.loads(path.read_text())["records"]["skills"] == []
    assert len(writer.list("skills")) == 1
    writer_db.close()


def test_backup_compares_timestamp_instants(service, tmp_path):
    from mycmd.core.backup import checksum

    service.create("projects", EXAMPLES["projects"])
    path = tmp_path / "timestamp.json"
    export_backup(service, path)
    body = json.loads(path.read_text())
    body.pop("checksum")
    entry = body["records"]["projects"][0]
    entry["created_at"] = "2026-01-01T00:00:00Z"
    entry["updated_at"] = "2026-01-01T00:00:00.100000+00:00"
    body["checksum"] = checksum(body)
    path.write_text(json.dumps(body))
    db = connect(tmp_path / "timestamp.db")
    report = import_backup(Service(db, service.owner_id), path, dry_run=False)
    assert report["invalid"] == 0 and report["additions"] == 1
    db.close()
