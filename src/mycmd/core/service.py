"""Owner-scoped local CRUD. Every mutation and its outbox entry commit together."""

import builtins
import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from mycmd.core.models import FIELDS, Record, ValidationError, uuid_text, validate


class ConflictError(ValueError):
    """The caller edited an old revision or violated a unique key."""


class NotFoundError(LookupError):
    """No visible record exists within this owner scope."""


def now() -> str:
    return datetime.now(UTC).isoformat()


def decode(row: sqlite3.Row) -> Record:
    values = dict(row)
    values["data"] = json.loads(values["data"])
    return Record(**values)


class Service:
    def __init__(self, db: sqlite3.Connection, owner_id: str):
        self.db = db
        self.owner_id = uuid_text(owner_id)
        self.db.execute(
            "INSERT OR IGNORE INTO local_sync_state(owner_id, device_id) VALUES (?, ?)",
            (self.owner_id, str(uuid4())),
        )
        self.device_id: str = self.db.execute(
            "SELECT device_id FROM local_sync_state WHERE owner_id = ?", (self.owner_id,)
        ).fetchone()[0]

    def get(self, record_id: str, *, include_deleted: bool = False) -> Record:
        row = self.db.execute(
            "SELECT * FROM records WHERE id = ? AND owner_id = ?",
            (uuid_text(record_id), self.owner_id),
        ).fetchone()
        if row is None or (row["deleted_at"] and not include_deleted):
            raise NotFoundError(record_id)
        return decode(row)

    def list(self, kind: str, *, include_deleted: bool = False) -> list[Record]:
        if kind not in FIELDS:
            raise ValidationError("Unknown entity type")
        rows = self.db.execute(
            "SELECT * FROM records WHERE owner_id = ? AND kind = ? "
            "AND (? OR deleted_at IS NULL) ORDER BY created_at, id",
            (self.owner_id, kind, include_deleted),
        ).fetchall()
        return [decode(row) for row in rows]

    def create(self, kind: str, data: dict[str, object]) -> Record:
        stamp = now()
        record = Record(
            str(uuid4()),
            self.owner_id,
            kind,
            validate(kind, data),
            stamp,
            stamp,
            1,
            None,
            "pending",
            0,
        )
        return self._mutate(record, "create", None)

    def update(
        self, record_id: str, changes: dict[str, object], *, expected_version: int
    ) -> Record:
        old = self.get(record_id)
        if type(expected_version) is not int or expected_version != old.version:
            raise ConflictError("Record changed; reload before editing")
        record = Record(
            old.id,
            old.owner_id,
            old.kind,
            validate(old.kind, old.data | changes),
            old.created_at,
            now(),
            old.version + 1,
            None,
            "pending",
            old.last_server_version,
        )
        return self._mutate(record, "update", expected_version)

    def delete(self, record_id: str, *, expected_version: int) -> Record:
        old = self.get(record_id)
        if type(expected_version) is not int or expected_version != old.version:
            raise ConflictError("Record changed; reload before editing")
        stamp = now()
        record = Record(
            old.id,
            old.owner_id,
            old.kind,
            old.data,
            old.created_at,
            stamp,
            old.version + 1,
            stamp,
            "pending",
            old.last_server_version,
        )
        return self._mutate(record, "delete", expected_version)

    def _write(self, record: Record, action: str, expected_version: int | None) -> None:
        values = asdict(record)
        values["data"] = json.dumps(record.data, sort_keys=True)
        if action == "create":
            self.db.execute(
                "INSERT INTO records VALUES (:id,:owner_id,:kind,:data,:created_at,"
                ":updated_at,:version,:deleted_at,:sync_status,:last_server_version)",
                values,
            )
        else:
            values["expected"] = expected_version
            changed = self.db.execute(
                "UPDATE records SET data=:data,updated_at=:updated_at,version=:version,"
                "deleted_at=:deleted_at,sync_status=:sync_status "
                "WHERE id=:id AND owner_id=:owner_id "
                "AND version=:expected AND deleted_at IS NULL",
                values,
            ).rowcount
            if changed != 1:
                raise ConflictError("Record changed; reload before editing")
        self.db.execute(
            "INSERT INTO local_outbox(operation_id,owner_id,device_id,entity_type,entity_id,"
            "action,base_version,payload_json) VALUES (?,?,?,?,?,?,?,?)",
            (
                str(uuid4()),
                self.owner_id,
                self.device_id,
                record.kind,
                record.id,
                action,
                record.last_server_version,
                json.dumps(asdict(record), sort_keys=True),
            ),
        )

    def _mutate(self, record: Record, action: str, expected_version: int | None) -> Record:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._write(record, action, expected_version)
            self.db.commit()
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Unique key or database constraint violation") from exc
        except Exception:
            self.db.rollback()
            raise
        return record

    def pending(self) -> builtins.list[dict[str, object]]:
        return [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM local_outbox WHERE owner_id = ? "
                "AND state = 'pending' ORDER BY sequence",
                (self.owner_id,),
            )
        ]
