"""Checksummed owner-scoped backups and conservative, atomic restore."""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

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


BACKUP_FORMAT_VERSION = 2
APPLICATION_VERSION = "2.0.0.dev0"


def _manifest_path(backup_path: Path) -> Path:
    return backup_path.with_suffix(backup_path.suffix + ".manifest.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".mycmd-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def create_sqlite_backup(
    live_database: Path,
    output: Path,
    *,
    owner_id: str,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Backup output already exists")
    if _manifest_path(output).exists():
        raise FileExistsError("Backup manifest already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=output.parent, prefix=".mycmd-", suffix=".tmp")
    os.close(fd)
    try:
        source = sqlite3.connect(live_database)
        destination = sqlite3.connect(temporary)
        try:
            source.backup(destination)
            destination.execute(
                "CREATE TABLE IF NOT EXISTS mycmd_backup_manifest("
                "format_version INTEGER NOT NULL,"
                "schema_version INTEGER NOT NULL,"
                "application_version TEXT NOT NULL,"
                "backup_type TEXT NOT NULL,"
                "created_at TEXT NOT NULL,"
                "owner_id TEXT NOT NULL)"
            )
            created_at = now()
            destination.execute(
                "INSERT INTO mycmd_backup_manifest("
                "format_version,schema_version,application_version,backup_type,"
                "created_at,owner_id"
                ") VALUES(?,?,?,?,?,?)",
                (
                    BACKUP_FORMAT_VERSION,
                    2,
                    APPLICATION_VERSION,
                    "sqlite",
                    created_at,
                    owner_id,
                ),
            )
            destination.commit()
        finally:
            destination.close()
            source.close()
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        digest = _sha256_file(output)
        manifest = {
            "format_version": BACKUP_FORMAT_VERSION,
            "schema_version": 2,
            "application_version": APPLICATION_VERSION,
            "backup_type": "sqlite",
            "created_at": created_at,
            "owner_id": owner_id,
            "database_sha256": digest,
            "encrypted": False,
            "components": [
                "records",
                "local_sync_state",
                "local_outbox",
                "local_conflicts",
                "sync_status",
            ],
        }
        _atomic_manifest(_manifest_path(output), manifest)
        verify_sqlite_backup(output, owner_id=owner_id)
        return manifest
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_sqlite_backup(
    backup_path: Path,
    *,
    owner_id: str | None = None,
) -> dict[str, Any]:
    if not backup_path.is_file():
        raise ValidationError("Backup file does not exist")
    manifest_path = _manifest_path(backup_path)
    if not manifest_path.is_file():
        raise ValidationError("Backup manifest does not exist")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid backup manifest") from exc
    if not isinstance(manifest, dict):
        raise ValidationError("Invalid backup manifest")
    required = {
        "format_version",
        "schema_version",
        "application_version",
        "backup_type",
        "created_at",
        "owner_id",
        "database_sha256",
        "encrypted",
        "components",
    }
    if set(manifest) != required:
        raise ValidationError("Invalid backup manifest fields")
    if manifest["format_version"] != BACKUP_FORMAT_VERSION:
        raise ValidationError("Unsupported backup format")
    if manifest["backup_type"] != "sqlite":
        raise ValidationError("Unexpected backup type")
    if manifest["encrypted"] is not False:
        raise ValidationError("Encrypted backup requires decryption")
    utc_timestamp(str(manifest["created_at"]))
    if owner_id is not None and manifest["owner_id"] != owner_id:
        raise ValidationError("Backup owner does not match the active owner")
    actual = _sha256_file(backup_path)
    if not hmac.compare_digest(actual, str(manifest["database_sha256"])):
        raise ValidationError("Backup checksum mismatch")
    db = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    try:
        integrity = db.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ValidationError("SQLite backup failed integrity check")
        version = db.execute("PRAGMA user_version").fetchone()
        if version is None or version[0] not in (1, 2):
            raise ValidationError("Unsupported SQLite backup schema")
        row = db.execute(
            "SELECT format_version,schema_version,application_version,"
            "backup_type,created_at,owner_id "
            "FROM mycmd_backup_manifest"
        ).fetchone()
        if row is None or tuple(row)[:5] != (
            BACKUP_FORMAT_VERSION,
            manifest["schema_version"],
            manifest["application_version"],
            "sqlite",
            manifest["created_at"],
        ):
            raise ValidationError("Backup manifest does not match database")
        if row[5] != manifest["owner_id"]:
            raise ValidationError("Backup database owner mismatch")
    except sqlite3.DatabaseError as exc:
        raise ValidationError("Corrupt SQLite backup") from exc
    finally:
        db.close()
    return manifest


def restore_sqlite_backup(
    live_database: Path,
    backup_path: Path,
    *,
    owner_id: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    manifest = verify_sqlite_backup(backup_path, owner_id=owner_id)
    if dry_run:
        db = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
        try:
            record_count = int(db.execute("SELECT COUNT(*) FROM records").fetchone()[0])
            pending_count = int(
                db.execute("SELECT COUNT(*) FROM local_outbox WHERE state='pending'").fetchone()[0]
            )
            conflict_count = int(
                db.execute(
                    "SELECT COUNT(*) FROM local_conflicts WHERE owner_id=? AND state='pending'",
                    (owner_id,),
                ).fetchone()[0]
            )
            return {
                "status": "dry-run",
                "records": record_count,
                "pending_operations": pending_count,
                "pending_conflicts": conflict_count,
                "manifest": manifest,
            }
        finally:
            db.close()
    live_database.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(dir=live_database.parent, prefix=".mycmd-restore-", suffix=".tmp")
    os.close(fd)
    os.unlink(staged)
    staged_path = Path(staged)
    rollback: Path | None = None
    try:
        backup = sqlite3.connect(backup_path)
        destination = sqlite3.connect(staged_path)
        try:
            backup.backup(destination)
        finally:
            destination.close()
            backup.close()
        verify_sqlite_backup(backup_path, owner_id=owner_id)
        staged_db = sqlite3.connect(f"file:{staged_path}?mode=ro", uri=True)
        try:
            integrity = staged_db.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise ValidationError("Restored SQLite database failed integrity check")
        finally:
            staged_db.close()
        if live_database.exists():
            fd, rollback_name = tempfile.mkstemp(
                dir=live_database.parent,
                prefix=".mycmd-rollback-",
                suffix=".tmp",
            )
            os.close(fd)
            rollback = Path(rollback_name)
            os.unlink(rollback)
            os.replace(live_database, rollback)
        os.replace(staged_path, live_database)
        return {"status": "restored", "manifest": manifest}
    except Exception:
        if rollback is not None and rollback.exists():
            if live_database.exists():
                os.unlink(live_database)
            os.replace(rollback, live_database)
        raise
    finally:
        if staged_path.exists():
            os.unlink(staged_path)
        if rollback is not None and rollback.exists():
            os.unlink(rollback)


def encrypt_sqlite_backup(
    backup_path: Path,
    output: Path,
    *,
    password: str,
    owner_id: str,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Encrypted backup output already exists")
    manifest = verify_sqlite_backup(backup_path, owner_id=owner_id)
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:
        raise RuntimeError("Encrypted backups require the cryptography dependency") from exc
    plaintext = backup_path.read_bytes()
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    token = Fernet(key).encrypt(plaintext)
    envelope = {
        "format_version": BACKUP_FORMAT_VERSION,
        "algorithm": "Fernet-PBKDF2-SHA256",
        "kdf_iterations": 600_000,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ciphertext": base64.b64encode(token).decode("ascii"),
    }
    fd, temporary = tempfile.mkstemp(dir=output.parent, prefix=".mycmd-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(envelope, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    encrypted_digest = _sha256_file(output)
    encrypted_manifest = dict(manifest)
    encrypted_manifest.update(
        {
            "backup_type": "sqlite-encrypted",
            "encrypted": True,
            "encrypted_sha256": encrypted_digest,
        }
    )
    encrypted_manifest["components"] = manifest["components"]
    _atomic_manifest(_manifest_path(output), encrypted_manifest)
    verify_encrypted_sqlite_backup(output, password=password, owner_id=owner_id)
    return encrypted_manifest


def verify_encrypted_sqlite_backup(
    backup_path: Path,
    *,
    password: str,
    owner_id: str | None = None,
) -> dict[str, Any]:
    manifest_path = _manifest_path(backup_path)
    if not backup_path.is_file() or not manifest_path.is_file():
        raise ValidationError("Encrypted backup or manifest does not exist")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        envelope = json.loads(backup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid encrypted backup") from exc
    if not isinstance(manifest, dict) or not isinstance(envelope, dict):
        raise ValidationError("Invalid encrypted backup")
    required = {
        "format_version",
        "schema_version",
        "application_version",
        "backup_type",
        "created_at",
        "owner_id",
        "database_sha256",
        "encrypted",
        "encrypted_sha256",
        "components",
    }
    if set(manifest) != required:
        raise ValidationError("Invalid encrypted backup manifest")
    if manifest["format_version"] != BACKUP_FORMAT_VERSION:
        raise ValidationError("Unsupported encrypted backup format")
    database_digest = str(manifest["database_sha256"])
    if len(database_digest) != 64 or any(
        char not in "0123456789abcdef" for char in database_digest
    ):
        raise ValidationError("Invalid encrypted backup checksum")
    utc_timestamp(str(manifest["created_at"]))
    if manifest.get("encrypted") is not True:
        raise ValidationError("Backup is not marked encrypted")
    if manifest.get("backup_type") != "sqlite-encrypted":
        raise ValidationError("Unexpected encrypted backup type")
    if owner_id is not None and manifest.get("owner_id") != owner_id:
        raise ValidationError("Encrypted backup owner mismatch")
    if not hmac.compare_digest(
        _sha256_file(backup_path),
        str(manifest.get("encrypted_sha256", "")),
    ):
        raise ValidationError("Encrypted backup checksum mismatch")
    if (
        envelope.get("format_version") != BACKUP_FORMAT_VERSION
        or envelope.get("algorithm") != "Fernet-PBKDF2-SHA256"
        or type(envelope.get("kdf_iterations")) is not int
        or envelope["kdf_iterations"] < 600_000
    ):
        raise ValidationError("Unsupported encrypted backup format")
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        salt = base64.b64decode(envelope["salt"], validate=True)
        token = base64.b64decode(envelope["ciphertext"], validate=True)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=int(envelope["kdf_iterations"]),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        Fernet(key).decrypt(token)
    except (KeyError, ValueError, InvalidToken) as exc:
        raise ValidationError("Wrong encryption key or corrupted ciphertext") from exc
    return manifest


def decrypt_sqlite_backup(
    encrypted_path: Path,
    output: Path,
    *,
    password: str,
    owner_id: str,
) -> Path:
    verify_encrypted_sqlite_backup(encrypted_path, password=password, owner_id=owner_id)
    if output.exists():
        raise FileExistsError("Decrypted backup output already exists")
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        envelope = json.loads(encrypted_path.read_text(encoding="utf-8"))
        salt = base64.b64decode(envelope["salt"], validate=True)
        token = base64.b64decode(envelope["ciphertext"], validate=True)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=int(envelope["kdf_iterations"]),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        plaintext = Fernet(key).decrypt(token)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ValidationError("Unable to decrypt SQLite backup") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=output.parent, prefix=".mycmd-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(plaintext)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    original_manifest = json.loads(_manifest_path(encrypted_path).read_text(encoding="utf-8"))
    original_manifest.update(
        {
            "backup_type": "sqlite",
            "encrypted": False,
        }
    )
    original_manifest.pop("encrypted_sha256", None)
    original_manifest["database_sha256"] = _sha256_file(output)
    _atomic_manifest(_manifest_path(output), original_manifest)
    verify_sqlite_backup(output, owner_id=owner_id)
    return output
