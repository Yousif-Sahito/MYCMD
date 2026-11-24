"""Durable local sync coordinator."""

import json
import sqlite3
import time
from typing import Any, cast

from mycmd.api_client.client import ApiClient, ApiError
from mycmd.core.service import Service

BATCH_SIZE = 100
MAX_ATTEMPTS = 8


class SyncCoordinator:
    def __init__(
        self,
        service: Service,
        client: ApiClient,
        *,
        sleep: Any = time.sleep,
    ):
        self.service = service
        self.client = client
        self.sleep = sleep

    def status(self) -> dict[str, object]:
        db = self.service.db
        pending = len(self.service.pending())
        retrying = db.execute(
            "SELECT COUNT(*) FROM local_outbox WHERE owner_id=? AND state='retry_wait'",
            (self.service.owner_id,),
        ).fetchone()[0]
        conflicts = db.execute(
            "SELECT COUNT(*) FROM local_conflicts WHERE owner_id=? AND state='pending'",
            (self.service.owner_id,),
        ).fetchone()[0]
        row = db.execute(
            "SELECT last_cursor,last_success_at,status,last_error "
            "FROM sync_status WHERE owner_id=?",
            (self.service.owner_id,),
        ).fetchone()
        return {
            "pending": pending,
            "retrying": retrying,
            "conflicts": conflicts,
            "cursor": row["last_cursor"] if row else 0,
            "last_success_at": row["last_success_at"] if row else None,
            "status": row["status"] if row else "idle",
            "last_error": row["last_error"] if row else None,
        }

    def dry_run(self) -> list[dict[str, object]]:
        return self.service.pending()[:BATCH_SIZE]

    def conflicts(self) -> list[dict[str, object]]:
        rows = self.service.db.execute(
            "SELECT * FROM local_conflicts "
            "WHERE owner_id=? AND state='pending' ORDER BY created_at",
            (self.service.owner_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def resolve_keep_server(self, conflict_id: str) -> dict[str, object]:
        row = self._conflict_row(conflict_id)
        server_json = row["server_json"]
        server = json.loads(str(server_json)) if isinstance(server_json, str) else None
        if not isinstance(server, dict):
            raise ValueError("Server record is unavailable")
        data = server.get("data")
        if not isinstance(data, dict):
            raise ValueError("Server record payload is invalid")
        db = self.service.db
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "UPDATE records SET data=?,updated_at=?,version=?,deleted_at=?,"
                "sync_status='synced',last_server_version=? "
                "WHERE id=? AND owner_id=?",
                (
                    json.dumps(data, sort_keys=True),
                    str(server.get("updated_at") or self._timestamp()),
                    int(server.get("version") or 1),
                    server.get("deleted_at"),
                    int(server.get("version") or 1),
                    row["entity_id"],
                    self.service.owner_id,
                ),
            )
            db.execute(
                "UPDATE local_conflicts SET state='resolved_keep_server',resolved_at=? "
                "WHERE id=? AND owner_id=?",
                (self._timestamp(), conflict_id, self.service.owner_id),
            )
            db.execute(
                "UPDATE local_outbox SET state='acknowledged',last_error=NULL "
                "WHERE operation_id=? AND owner_id=?",
                (conflict_id, self.service.owner_id),
            )
            db.commit()
        except (sqlite3.Error, ValueError):
            db.rollback()
            raise
        return {"status": "resolved", "resolution": "keep_server"}

    def resolve_keep_local(self, conflict_id: str) -> dict[str, object]:
        row = self._conflict_row(conflict_id)
        local_json = str(row["local_json"])
        local_payload = cast(dict[str, Any], json.loads(local_json))
        local_data = local_payload.get("data")
        if not isinstance(local_data, dict):
            raise ValueError("Local record payload is unavailable")
        return self._resolve_with_payload(
            conflict_id,
            row,
            local_data,
            "keep_local",
        )

    def resolve_manual_merge(
        self,
        conflict_id: str,
        merged_data: dict[str, Any],
    ) -> dict[str, object]:
        row = self._conflict_row(conflict_id)
        kind = str(row["entity_type"])
        try:
            from mycmd.core.models import validate

            validated = validate(kind, merged_data)
        except Exception as exc:
            raise ValueError(str(exc)) from exc
        return self._resolve_with_payload(conflict_id, row, validated, "manual_merge")

    def _resolve_with_payload(
        self,
        conflict_id: str,
        row: dict[str, object],
        payload: dict[str, Any],
        resolution: str,
    ) -> dict[str, object]:
        server = json.loads(str(row["server_json"])) if row["server_json"] else None
        if not isinstance(server, dict):
            raise ValueError("Server record is unavailable")
        server_version = int(server.get("version") or 1)
        operation_id = str(__import__("uuid").uuid4())
        kind = str(row["entity_type"])
        entity_id = str(row["entity_id"])
        db = self.service.db
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "INSERT INTO local_outbox("
                "operation_id,owner_id,device_id,entity_type,entity_id,"
                "action,base_version,payload_json,state"
                ") VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    self.service.owner_id,
                    self.service.device_id,
                    kind,
                    entity_id,
                    "update",
                    server_version,
                    json.dumps(
                        {
                            "id": entity_id,
                            "owner_id": self.service.owner_id,
                            "kind": kind,
                            "data": payload,
                            "version": server_version,
                        },
                        sort_keys=True,
                    ),
                    "pending",
                ),
            )
            db.execute(
                "UPDATE local_conflicts SET state='resolution_pending',resolved_at=NULL "
                "WHERE id=? AND owner_id=?",
                (conflict_id, self.service.owner_id),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise
        return {
            "status": "queued",
            "resolution": resolution,
            "operation_id": operation_id,
        }

    def _conflict_row(self, conflict_id: str) -> dict[str, object]:
        row = self.service.db.execute(
            "SELECT * FROM local_conflicts WHERE id=? AND owner_id=? AND state='pending'",
            (conflict_id, self.service.owner_id),
        ).fetchone()
        if row is None:
            raise LookupError("Conflict not found")
        return dict(row)

    def recover_inflight(self) -> int:
        db = self.service.db
        cursor = db.execute(
            "UPDATE local_outbox SET state='pending', next_retry_at=NULL "
            "WHERE owner_id=? AND state='in_flight'",
            (self.service.owner_id,),
        ).rowcount
        db.commit()
        return cursor

    def run(self) -> dict[str, object]:
        self.recover_inflight()
        rows = self.service.pending()[:BATCH_SIZE]
        if not rows:
            return self._pull()

        operations = [
            {
                "operation_id": row["operation_id"],
                "device_id": row["device_id"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "action": row["action"],
                "base_version": row["base_version"],
                "payload": self._payload(row),
            }
            for row in rows
        ]
        db = self.service.db
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE local_outbox SET state='in_flight', attempts=attempts+1 "
                "WHERE owner_id=? AND sequence IN ({})".format(",".join("?" for _ in rows)),
                (self.service.owner_id, *[row["sequence"] for row in rows]),
            )
            db.commit()
        except sqlite3.Error as exc:
            db.rollback()
            return self._error("retry_wait", str(exc))

        try:
            response = self.client.push(operations)
        except ApiError as exc:
            self._set_retry(rows, exc.category)
            return self._error(exc.category, str(exc))

        results = response.get("results")
        if not isinstance(results, list):
            return self._error("invalid_response", "Push response has no results")
        accepted = 0
        conflicts = 0
        for result in results:
            if not isinstance(result, dict):
                continue
            operation_id = str(result.get("operation_id", ""))
            status = result.get("status")
            if status == "accepted":
                accepted += 1
                self._acknowledge(operation_id)
            elif status == "conflict":
                conflicts += 1
                self._preserve_conflict(operation_id, result)
            elif status == "rejected":
                self._reject(operation_id, str(result.get("error") or "Rejected"))
        if conflicts:
            return self._error("conflicts_pending", f"{conflicts} synchronization conflict(s)")
        if accepted:
            return self._pull()
        return self.status()

    def _pull(self) -> dict[str, object]:
        db = self.service.db
        row = db.execute(
            "SELECT last_cursor FROM sync_status WHERE owner_id=?",
            (self.service.owner_id,),
        ).fetchone()
        cursor = int(row["last_cursor"]) if row else 0
        while True:
            try:
                page = self.client.pull(cursor, 100)
            except ApiError as exc:
                self._set_retry([], exc.category)
                return self._error(exc.category, str(exc))
            items = page.get("items")
            next_cursor = page.get("next_cursor")
            if not isinstance(items, list) or type(next_cursor) is not int:
                return self._error("invalid_response", "Pull response is invalid")
            db.execute("BEGIN IMMEDIATE")
            try:
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError("Invalid pull item")
                    self._apply_change(item)
                db.execute(
                    "INSERT INTO sync_status("
                    "owner_id,last_cursor,last_success_at,status,last_error"
                    ") "
                    "VALUES(?,?,?,?,?) "
                    "ON CONFLICT(owner_id) DO UPDATE SET "
                    "last_cursor=excluded.last_cursor,last_success_at=excluded.last_success_at,"
                    "status='idle',last_error=NULL",
                    (self.service.owner_id, next_cursor, self._timestamp(), "idle", None),
                )
                db.commit()
            except (sqlite3.Error, ValueError) as exc:
                db.rollback()
                return self._error("retry_wait", str(exc))
            cursor = next_cursor
            if len(items) < 100:
                break
        return self.status()

    def _apply_change(self, item: dict[str, Any]) -> None:
        entity_id = str(item["entity_id"])
        kind = str(item["entity_type"])
        if item["tombstone"]:
            self.service.db.execute(
                "UPDATE records SET deleted_at=?,sync_status='synced',version=? "
                "WHERE id=? AND owner_id=?",
                (self._timestamp(), int(item["version"]), entity_id, self.service.owner_id),
            )
            return
        record = item["record"]
        if not isinstance(record, dict):
            raise ValueError("Missing record payload")
        data = record["data"]
        if not isinstance(data, dict):
            raise ValueError("Invalid record payload")
        old = self.service.db.execute(
            "SELECT version,sync_status FROM records WHERE id=? AND owner_id=?",
            (entity_id, self.service.owner_id),
        ).fetchone()
        if old is not None and old["sync_status"] == "pending":
            return
        values = (
            entity_id,
            self.service.owner_id,
            kind,
            json.dumps(data, sort_keys=True),
            str(record["created_at"]),
            str(record["updated_at"]),
            int(record["version"]),
            None,
            "synced",
            int(record["version"]),
        )
        self.service.db.execute(
            "INSERT INTO records("
            "id,owner_id,kind,data,created_at,updated_at,version,deleted_at,"
            "sync_status,last_server_version"
            ") VALUES(?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data,"
            "updated_at=excluded.updated_at,version=excluded.version,"
            "deleted_at=NULL,sync_status='synced',"
            "last_server_version=excluded.last_server_version "
            "WHERE records.owner_id=excluded.owner_id",
            values,
        )

    def _acknowledge(self, operation_id: str) -> None:
        db = self.service.db
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "UPDATE local_outbox SET state='acknowledged' WHERE operation_id=? AND owner_id=?",
                (operation_id, self.service.owner_id),
            )
            db.execute(
                "UPDATE records SET sync_status='synced' "
                "WHERE id=(SELECT entity_id FROM local_outbox WHERE operation_id=? AND owner_id=?) "
                "AND owner_id=?",
                (operation_id, self.service.owner_id, self.service.owner_id),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()

    def _preserve_conflict(self, operation_id: str, result: dict[str, Any]) -> None:
        db = self.service.db
        row = db.execute(
            "SELECT * FROM local_outbox WHERE operation_id=? AND owner_id=?",
            (operation_id, self.service.owner_id),
        ).fetchone()
        if row is None:
            return
        payload = json.loads(row["payload_json"])
        server = result.get("server_record")
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "UPDATE local_outbox SET state='conflict',last_error=? "
                "WHERE operation_id=? AND owner_id=?",
                (str(result.get("error") or "Conflict"), operation_id, self.service.owner_id),
            )
            db.execute(
                "INSERT INTO local_conflicts("
                "id,owner_id,entity_type,entity_id,local_json,server_json,"
                "local_version,server_version,conflict_type,state,created_at,resolved_at"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL) "
                "ON CONFLICT(owner_id,entity_type,entity_id) DO UPDATE SET "
                "local_json=excluded.local_json,server_json=excluded.server_json,"
                "local_version=excluded.local_version,server_version=excluded.server_version,"
                "conflict_type=excluded.conflict_type,state='pending'",
                (
                    operation_id,
                    self.service.owner_id,
                    row["entity_type"],
                    row["entity_id"],
                    json.dumps(payload, sort_keys=True),
                    json.dumps(server, sort_keys=True) if server is not None else None,
                    int(str(payload.get("version") or 1)),
                    int(str(server.get("version")))
                    if isinstance(server, dict) and server.get("version") is not None
                    else None,
                    "optimistic_version",
                    "pending",
                    self._timestamp(),
                ),
            )
            db.execute(
                "UPDATE records SET sync_status='conflict' WHERE id=? AND owner_id=?",
                (row["entity_id"], self.service.owner_id),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()

    def _reject(self, operation_id: str, message: str) -> None:
        self.service.db.execute("BEGIN IMMEDIATE")
        try:
            self.service.db.execute(
                "UPDATE local_outbox SET state='failed_permanently',last_error=? "
                "WHERE operation_id=? AND owner_id=?",
                (message, operation_id, self.service.owner_id),
            )
            self.service.db.commit()
        except sqlite3.Error:
            self.service.db.rollback()

    def _set_retry(self, rows: list[dict[str, object]], category: str) -> None:
        db = self.service.db
        db.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                raw_attempts = row["attempts"]
                attempts = int(str(raw_attempts)) + 1
                if attempts >= MAX_ATTEMPTS:
                    state = "failed_permanently"
                    delay = None
                else:
                    state = "retry_wait"
                    delay = f"+{min(300, 2**attempts)} seconds"
                db.execute(
                    "UPDATE local_outbox SET state=?,attempts=?,"
                    "next_retry_at=CASE WHEN ? IS NULL THEN NULL "
                    "ELSE strftime('%Y-%m-%dT%H:%M:%fZ','now',?) END,"
                    "last_error=? WHERE operation_id=? AND owner_id=?",
                    (
                        state,
                        attempts,
                        delay,
                        delay,
                        category,
                        row["operation_id"],
                        self.service.owner_id,
                    ),
                )
            db.commit()
        except sqlite3.Error:
            db.rollback()

    def _error(self, status: str, message: str) -> dict[str, object]:
        db = self.service.db
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "INSERT INTO sync_status(owner_id,last_cursor,last_success_at,status,last_error) "
                "VALUES(?,0,NULL,?,?) "
                "ON CONFLICT(owner_id) DO UPDATE SET "
                "status=excluded.status,last_error=excluded.last_error",
                (self.service.owner_id, status, message),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()
        return {"status": status, "error": message}

    @staticmethod
    def _payload(row: dict[str, object]) -> dict[str, Any]:
        payload = cast(dict[str, Any], json.loads(str(row["payload_json"])))
        if row["action"] == "create":
            return cast(dict[str, Any], payload["data"])
        if row["action"] == "delete":
            return {}
        return cast(dict[str, Any], payload["data"])

    @staticmethod
    def _timestamp() -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()
