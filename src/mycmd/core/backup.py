"""Checksummed owner-scoped backups and conservative, atomic restore."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from mycmd.core.models import FIELDS, Record, ValidationError, utc_timestamp, uuid_text, validate
from mycmd.core.service import Service, now


def checksum(body: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def export_backup(service: Service, path: Path) -> None:
    service.db.execute("BEGIN")
    try:
        records = {
            kind: [asdict(r) for r in service.list(kind, include_deleted=True)] for kind in FIELDS
        }
        service.db.commit()
    except Exception:
        service.db.rollback()
        raise
    body: dict[str, object] = {
        "schema_version": 1,
        "exported_at": now(),
        "owner_id": service.owner_id,
        "records": records,
    }
    body["checksum"] = checksum(body)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".mycmd-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(body, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def import_backup(service: Service, path: Path, *, dry_run: bool = True) -> dict[str, int]:
    report = {"additions": 0, "changes": 0, "conflicts": 0, "invalid": 0, "unchanged": 0}
    candidates: list[Record] = []
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(body, dict):
            raise ValueError
        digest = body.pop("checksum")
        if digest != checksum(body) or set(body) != {
            "schema_version",
            "exported_at",
            "owner_id",
            "records",
        }:
            raise ValueError
        if type(body["schema_version"]) is not int or body["schema_version"] != 1:
            raise ValueError
        if body["owner_id"] != service.owner_id or set(body["records"]) != set(FIELDS):
            raise ValueError
        utc_timestamp(body["exported_at"])
        seen: set[str] = set()
        for kind, entries in body["records"].items():
            if not isinstance(entries, list):
                raise ValueError
            for entry in entries:
                try:
                    record = Record(**entry)
                    if record.kind != kind or record.owner_id != service.owner_id:
                        raise ValueError
                    if uuid_text(record.id) != record.id or record.id in seen:
                        raise ValueError
                    seen.add(record.id)
                    validate(kind, record.data)
                    utc_timestamp(record.created_at)
                    utc_timestamp(record.updated_at)
                    if datetime.fromisoformat(record.updated_at) < datetime.fromisoformat(
                        record.created_at
                    ):
                        raise ValueError
                    if record.deleted_at is not None:
                        utc_timestamp(record.deleted_at)
                        if datetime.fromisoformat(record.deleted_at) != datetime.fromisoformat(
                            record.updated_at
                        ):
                            raise ValueError
                    if (
                        type(record.version) is not int
                        or record.version < 1
                        or type(record.last_server_version) is not int
                        or record.last_server_version < 0
                        or record.sync_status not in {"pending", "synced", "conflict"}
                    ):
                        raise ValueError
                    candidates.append(record)
                except (ValueError, TypeError, AttributeError):
                    report["invalid"] += 1
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValidationError("Invalid backup schema, checksum or owner scope") from exc

    service.db.execute("BEGIN IMMEDIATE")
    try:
        additions: list[Record] = []
        for record in candidates:
            existing = service.db.execute(
                "SELECT * FROM records WHERE id=?", (record.id,)
            ).fetchone()
            if existing is None:
                additions.append(record)
                report["additions"] += 1
            elif existing["owner_id"] != service.owner_id:
                report["conflicts"] += 1
            elif (
                json.loads(existing["data"]) == record.data
                and existing["kind"] == record.kind
                and existing["deleted_at"] == record.deleted_at
            ):
                report["unchanged"] += 1
            else:
                report["changes"] += 1
                report["conflicts"] += 1
        # Restore never silently overwrites existing edits. Unique collisions are
        # checked by real SQLite constraints, even in a dry run.
        if not report["invalid"] and not report["conflicts"]:
            for record in additions:
                restored = Record(
                    record.id,
                    record.owner_id,
                    record.kind,
                    record.data,
                    record.created_at,
                    record.updated_at,
                    record.version,
                    record.deleted_at,
                    "pending",
                    0,
                )
                service._write(restored, "create", None)
        if dry_run or report["invalid"] or report["conflicts"]:
            service.db.rollback()
        else:
            service.db.commit()
    except Exception:
        service.db.rollback()
        raise
    return report
