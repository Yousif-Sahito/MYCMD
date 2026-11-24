from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mycmd.core.models import ValidationError, validate
from server.app.db.models import Record


class RecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        owner_id: str,
        kind: str,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None,
    ) -> tuple[list[Record], int]:
        statement = select(Record).where(
            Record.owner_id == owner_id,
            Record.kind == kind,
            Record.deleted_at.is_(None),
        )
        if search:
            statement = statement.where(func.cast(Record.data, String).like(f"%{search}%"))
        if status:
            statement = statement.where(Record.data["status"].as_string() == status)
        count_statement = select(func.count()).select_from(statement.subquery())
        total = int(self.db.scalar(count_statement) or 0)
        rows = list(
            self.db.scalars(
                statement.order_by(Record.created_at.desc(), Record.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, total

    def get(self, owner_id: str, kind: str, record_id: str) -> Record | None:
        return self.db.scalar(
            select(Record).where(
                Record.owner_id == owner_id,
                Record.kind == kind,
                Record.id == record_id,
                Record.deleted_at.is_(None),
            )
        )

    def create(self, owner_id: str, kind: str, data: dict[str, Any]) -> Record:
        try:
            validated = validate(kind, data)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        record = Record(
            owner_id=owner_id,
            kind=kind,
            data=validated,
            version=1,
        )
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Unique key or database constraint violation") from exc
        self.db.refresh(record)
        return record

    def update(
        self,
        owner_id: str,
        kind: str,
        record_id: str,
        expected_version: int,
        changes: dict[str, Any],
    ) -> Record:
        record = self.db.scalar(
            select(Record)
            .where(
                Record.owner_id == owner_id,
                Record.kind == kind,
                Record.id == record_id,
                Record.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if record is None:
            raise LookupError("Record not found")
        if record.version != expected_version:
            raise TimeoutError("Record changed; reload before editing")
        merged = dict(record.data)
        merged.update(changes)
        try:
            validated = validate(kind, merged)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        record.data = validated
        record.version += 1
        record.updated_at = datetime.now(UTC)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Unique key or database constraint violation") from exc
        self.db.refresh(record)
        return record

    def delete(self, owner_id: str, kind: str, record_id: str, expected_version: int) -> Record:
        record = self.db.scalar(
            select(Record)
            .where(
                Record.owner_id == owner_id,
                Record.kind == kind,
                Record.id == record_id,
                Record.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if record is None:
            raise LookupError("Record not found")
        if record.version != expected_version:
            raise TimeoutError("Record changed; reload before editing")
        record.deleted_at = datetime.now(UTC)
        record.version += 1
        record.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(record)
        return record
