import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from mycmd.core.backup import (
    ValidationError,
    create_sqlite_backup,
    decrypt_sqlite_backup,
    encrypt_sqlite_backup,
    restore_sqlite_backup,
    verify_encrypted_sqlite_backup,
    verify_sqlite_backup,
)
from mycmd.core.service import Service
from mycmd.storage.database import connect


def test_sqlite_backup_restore_preserves_records_outbox_and_conflicts(tmp_path: Path) -> None:
    live = tmp_path / "live.sqlite3"
    db = connect(live)
    service = Service(db, str(uuid4()))
    record = service.create(
        "projects",
        {"slug": "backup-project", "title": "Backup project", "status": "active"},
    )
    db.execute(
        "INSERT INTO local_conflicts("
        "id,owner_id,entity_type,entity_id,local_json,server_json,"
        "local_version,server_version,conflict_type,state,created_at,resolved_at"
        ") VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)",
        (
            str(uuid4()),
            service.owner_id,
            "projects",
            record.id,
            json.dumps({"title": "Local"}),
            json.dumps({"title": "Server"}),
            1,
            2,
            "optimistic_version",
            "pending",
            record.updated_at,
        ),
    )
    db.commit()

    backup = tmp_path / "snapshot.sqlite3"
    manifest = create_sqlite_backup(live, backup, owner_id=service.owner_id)
    assert manifest["backup_type"] == "sqlite"
    assert verify_sqlite_backup(backup, owner_id=service.owner_id)["database_sha256"]

    dry = restore_sqlite_backup(
        live,
        backup,
        owner_id=service.owner_id,
        dry_run=True,
    )
    assert dry["status"] == "dry-run"
    assert dry["records"] == 1
    assert dry["pending_operations"] == 1
    assert dry["pending_conflicts"] == 1

    db.close()
    live.unlink()

    report = restore_sqlite_backup(
        live,
        backup,
        owner_id=service.owner_id,
        dry_run=False,
    )
    assert report["status"] == "restored"
    restored = connect(live)
    restored_service = Service(restored, service.owner_id)
    assert restored_service.get(record.id).data["title"] == "Backup project"
    assert len(restored_service.pending()) == 1
    assert (
        restored.execute(
            "SELECT COUNT(*) FROM local_conflicts WHERE owner_id=? AND state='pending'",
            (restored_service.owner_id,),
        ).fetchone()[0]
        == 1
    )
    restored.close()


def test_corrupt_and_wrong_key_backups_are_rejected(tmp_path: Path) -> None:
    live = tmp_path / "live.sqlite3"
    db = connect(live)
    service = Service(db, str(uuid4()))
    service.create(
        "projects",
        {"slug": "encrypted-project", "title": "Encrypted", "status": "active"},
    )
    db.close()

    backup = tmp_path / "snapshot.sqlite3"
    create_sqlite_backup(live, backup, owner_id=service.owner_id)
    backup.write_bytes(b"corrupt")
    with pytest.raises(ValidationError, match="checksum"):
        verify_sqlite_backup(backup, owner_id=service.owner_id)

    backup = tmp_path / "snapshot2.sqlite3"
    db = connect(live)
    create_sqlite_backup(live, backup, owner_id=service.owner_id)
    db.close()
    encrypted = tmp_path / "snapshot2.sqlite3.enc"
    encrypt_sqlite_backup(
        backup,
        encrypted,
        password="correct-key",
        owner_id=service.owner_id,
    )
    verify_encrypted_sqlite_backup(
        encrypted,
        password="correct-key",
        owner_id=service.owner_id,
    )
    with pytest.raises(ValidationError, match="Wrong encryption key|corrupted"):
        verify_encrypted_sqlite_backup(
            encrypted,
            password="wrong-key",
            owner_id=service.owner_id,
        )

    decrypted = tmp_path / "decrypted.sqlite3"
    decrypt_sqlite_backup(
        encrypted,
        decrypted,
        password="correct-key",
        owner_id=service.owner_id,
    )
    restored = sqlite3.connect(decrypted)
    assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    restored.close()


def test_restore_replaces_live_database_only_after_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = tmp_path / "live.sqlite3"
    db = connect(live)
    service = Service(db, str(uuid4()))
    original = service.create(
        "projects",
        {"slug": "original-project", "title": "Original", "status": "active"},
    )
    db.close()

    backup = tmp_path / "snapshot.sqlite3"
    create_sqlite_backup(live, backup, owner_id=service.owner_id)
    original_replace = __import__("os").replace

    def injected_replace(source: object, destination: object) -> object:
        source_path = Path(str(source))
        destination_path = Path(str(destination))
        if source_path.name.startswith(".mycmd-restore-") and destination_path == live:
            raise OSError("injected staged restore failure")
        return original_replace(source, destination)

    monkeypatch.setattr("os.replace", injected_replace)
    with pytest.raises(OSError, match="injected staged restore failure"):
        restore_sqlite_backup(
            live,
            backup,
            owner_id=service.owner_id,
            dry_run=False,
        )

    restored = connect(live)
    restored_service = Service(restored, service.owner_id)
    assert restored_service.get(original.id).data["title"] == "Original"
    assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    restored.close()
