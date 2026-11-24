from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mycmd.core.models import ValidationError, validate
from server.app.db.models import ChangeLog, Record, SyncCursor, SyncOperation


class SyncRepository:
    def __init__(self, db: Session):
        self.db = db

    def push(self, owner_id: str, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cursor = self.db.scalar(
            select(SyncCursor).where(SyncCursor.owner_id == owner_id).with_for_update()
        )
        if cursor is None:
            cursor = SyncCursor(owner_id=owner_id, sequence=0)
            self.db.add(cursor)
            self.db.flush()
        results: list[dict[str, Any]] = []
        try:
            for operation in operations:
                op_id = str(operation["operation_id"])
                existing = self.db.scalar(
                    select(SyncOperation).where(
                        SyncOperation.owner_id == owner_id,
                        SyncOperation.operation_id == op_id,
                    )
                )
                if existing is not None:
                    results.append(existing.response_json)
                    continue

                kind = operation["entity_type"]
                entity_id = str(operation["entity_id"])
                action = operation["action"]
                base_version = operation["base_version"]
                payload = operation["payload"]
                record = self.db.scalar(
                    select(Record)
                    .where(
                        Record.owner_id == owner_id,
                        Record.id == entity_id,
                        Record.kind == kind,
                    )
                    .with_for_update()
                )

                if action == "create":
                    if record is not None:
                        result = self._conflict(op_id, record, "Record already exists")
                    else:
                        try:
                            data = validate(kind, payload)
                        except ValidationError as exc:
                            result = self._rejected(op_id, str(exc))
                        else:
                            record = Record(
                                id=entity_id,
                                owner_id=owner_id,
                                kind=kind,
                                data=data,
                                version=1,
                            )
                            self.db.add(record)
                            self.db.flush()
                            result = self._accepted(op_id, record)
                            self._change(cursor, record, tombstone=False)
                elif record is None or record.deleted_at is not None:
                    result = self._conflict(op_id, record, "Record does not exist")
                elif record.version != base_version:
                    result = self._conflict(op_id, record, "Record changed")
                else:
                    if action == "update":
                        try:
                            data = validate(kind, dict(record.data) | payload)
                        except ValidationError as exc:
                            result = self._rejected(op_id, str(exc))
                        else:
                            record.data = data
                            record.version += 1
                            record.updated_at = datetime.now(UTC)
                            result = self._accepted(op_id, record)
                            self._change(cursor, record, tombstone=False)
                    else:
                        record.deleted_at = datetime.now(UTC)
                        record.version += 1
                        record.updated_at = datetime.now(UTC)
                        result = self._accepted(op_id, record)
                        self._change(cursor, record, tombstone=True)

                self.db.add(
                    SyncOperation(
                        owner_id=owner_id,
                        operation_id=op_id,
                        device_id=str(operation["device_id"]),
                        entity_type=kind,
                        entity_id=entity_id,
                        action=action,
                        base_version=base_version,
                        response_json=result,
                        committed_at=datetime.now(UTC),
                    )
                )
                self.db.flush()
                results.append(result)
            self.db.commit()
        except IntegrityError:
            operation_ids = [str(operation["operation_id"]) for operation in operations]
            self.db.rollback()
            replayed: list[dict[str, Any]] = []
            for operation_id in operation_ids:
                existing = self.db.scalar(
                    select(SyncOperation).where(
                        SyncOperation.owner_id == owner_id,
                        SyncOperation.operation_id == operation_id,
                    )
                )
                if existing is None:
                    raise
                replayed.append(existing.response_json)
            return replayed
        return results

    def pull(self, owner_id: str, cursor: int, limit: int) -> tuple[list[ChangeLog], int]:
        rows = list(
            self.db.scalars(
                select(ChangeLog)
                .where(ChangeLog.owner_id == owner_id, ChangeLog.sequence > cursor)
                .order_by(ChangeLog.sequence)
                .limit(limit)
            )
        )
        next_cursor = rows[-1].sequence if rows else cursor
        return rows, next_cursor

    def _change(self, cursor: SyncCursor, record: Record, *, tombstone: bool) -> None:
        payload = (
            None
            if tombstone
            else {
                "id": record.id,
                "kind": record.kind,
                "data": record.data,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "version": record.version,
                "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
            }
        )
        cursor.sequence += 1
        self.db.add(
            ChangeLog(
                sequence=cursor.sequence,
                owner_id=record.owner_id,
                entity_type=record.kind,
                entity_id=record.id,
                version=record.version,
                changed_at=datetime.now(UTC),
                tombstone=tombstone,
                record_json=payload,
            )
        )

    @staticmethod
    def _accepted(operation_id: str, record: Record) -> dict[str, Any]:
        return {
            "operation_id": operation_id,
            "status": "accepted",
            "record": SyncRepository._record(record),
            "server_record": None,
            "error": None,
        }

    @staticmethod
    def _conflict(operation_id: str, record: Record | None, message: str) -> dict[str, Any]:
        return {
            "operation_id": operation_id,
            "status": "conflict",
            "record": None,
            "server_record": SyncRepository._record(record) if record is not None else None,
            "error": message,
        }

    @staticmethod
    def _rejected(operation_id: str, message: str) -> dict[str, Any]:
        return {
            "operation_id": operation_id,
            "status": "rejected",
            "record": None,
            "server_record": None,
            "error": message,
        }

    @staticmethod
    def _record(record: Record) -> dict[str, Any]:
        return {
            "id": record.id,
            "kind": record.kind,
            "data": record.data,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "version": record.version,
            "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
        }
