"""MYCMD command line interface."""

import json
import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, NoReturn
from uuid import UUID

os.environ.setdefault("TYPER_USE_RICH", "0")
import typer

from mycmd.config import data_directory, owner_id
from mycmd.core.backup import (
    _manifest_path,
    create_sqlite_backup,
    decrypt_sqlite_backup,
    encrypt_sqlite_backup,
    restore_sqlite_backup,
    verify_encrypted_sqlite_backup,
    verify_sqlite_backup,
)
from mycmd.core.models import FIELDS, Record, ValidationError
from mycmd.core.service import ConflictError, NotFoundError, Service
from mycmd.storage.database import connect

app = typer.Typer(
    no_args_is_help=True,
    help="MYCMD 2.0 - Personal Command Centre",
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


@app.command()
def gui() -> None:
    """Launch the optional local desktop application."""
    try:
        from mycmd.gui.app import run
    except ImportError as exc:
        fail(f"Desktop dependencies unavailable. Install mycmd[gui]. {exc}", 3)
    raise typer.Exit(run())


ENTITY_FIELDS = {
    "projects": (
        "slug",
        "title",
        "status",
        "description",
        "technologies",
        "links",
        "started_at",
        "finished_at",
        "notes",
    ),
    "skills": ("name", "category", "level", "notes"),
    "education": ("institution", "program", "status", "started_at", "ended_at", "notes"),
    "certificates": (
        "name",
        "issuer",
        "credential_id",
        "credential_url",
        "issued_at",
        "expires_at",
        "notes",
    ),
    "milestones": ("title", "due_at", "priority", "status", "completed_at", "notes"),
}


def service() -> Service:
    root = data_directory()
    try:
        root.mkdir(parents=True, exist_ok=True)
        owner = os.environ.get("MYCMD_OWNER_ID", "00000000-0000-4000-8000-000000000001")
        return Service(connect(root / "mycmd.sqlite3"), owner)
    except (OSError, sqlite3.Error) as exc:
        fail(f"Cannot open local database at {root}: {exc}", 3)


def fail(message: str, code: int = 2) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code)


def render(records: Iterable[Record], kind: str) -> None:
    typer.echo(kind.title())
    for record in records:
        fields = "  ".join(f"{key}: {record.data.get(key, '')}" for key in ENTITY_FIELDS[kind][:4])
        typer.echo(f"{record.id}  {fields}")


def payload(kind: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in ENTITY_FIELDS[kind]:
        if field in {
            "description",
            "technologies",
            "links",
            "notes",
            "credential_id",
            "credential_url",
            "started_at",
            "finished_at",
            "ended_at",
            "issued_at",
            "expires_at",
            "due_at",
            "completed_at",
        }:
            continue
        value = typer.prompt(field.replace("_", " "))
        if field in {"technologies", "links"}:
            result[field] = [part.strip() for part in value.split(",") if part.strip()]
        else:
            result[field] = value
    return result


def group(kind: str) -> typer.Typer:
    cli = typer.Typer(
        help=f"Manage {kind}.",
        add_completion=False,
        rich_markup_mode=None,
        pretty_exceptions_enable=False,
    )

    @cli.command("list")
    def list_records(status: str | None = typer.Option(None, "--status")) -> None:
        rows = service().list(kind)
        if status:
            rows = [r for r in rows if r.data.get("status") == status]
        render(rows, kind)

    @cli.command("add")
    def add() -> None:
        try:
            record = service().create(kind, payload(kind))
            typer.echo(f"Created {record.id}")
        except (ValidationError, ConflictError) as exc:
            fail(str(exc))

    @cli.command("show")
    def show(record_id: str) -> None:
        try:
            record = service().get(str(UUID(record_id)))
            if record.kind != kind:
                fail("Record type does not match command", 4)
            for key, value in record.data.items():
                typer.echo(f"{key}: {value}")
            typer.echo(f"ID: {record.id}  Version: {record.version}")
        except ValueError as exc:
            fail(str(exc))
        except NotFoundError:
            fail("Record not found", 4)

    @cli.command("edit")
    def edit(
        record_id: str, field: str = typer.Argument(...), value: str = typer.Argument(...)
    ) -> None:
        if field not in FIELDS[kind]:
            fail("Unknown field")
        try:
            record = service().get(str(UUID(record_id)))
            changes: dict[str, object] = {field: value}
            if field in {"technologies", "links"}:
                changes[field] = [v.strip() for v in value.split(",") if v.strip()]
            result = service().update(record.id, changes, expected_version=record.version)
            typer.echo(f"Updated {result.id} (version {result.version})")
        except (ValueError, ValidationError, ConflictError, NotFoundError) as exc:
            fail(str(exc), 4)

    @cli.command()
    def archive(record_id: str) -> None:
        try:
            record = service().get(str(UUID(record_id)))
            if kind != "projects":
                fail("Archive applies to projects")
            result = service().update(
                record.id, {"status": "archived"}, expected_version=record.version
            )
            typer.echo(f"Archived {result.id}")
        except (ValueError, ValidationError, ConflictError, NotFoundError) as exc:
            fail(str(exc), 4)

    @cli.command()
    def delete(record_id: str, yes: bool = typer.Option(False, "--yes", "-y")) -> None:
        try:
            record = service().get(str(UUID(record_id)))
            if not yes:
                typer.confirm(f"Delete {record.id}?", abort=True)
            service().delete(record.id, expected_version=record.version)
            typer.echo(f"Deleted {record.id}")
        except (ValueError, ConflictError, NotFoundError) as exc:
            fail(str(exc), 4)

    return cli


for entity in ENTITY_FIELDS:
    app.add_typer(group(entity), name=entity)


@app.command()
def status() -> None:
    db = service()
    typer.echo("MYCMD local status")
    for entity in ENTITY_FIELDS:
        typer.echo(f"{entity}: {len(db.list(entity))}")
    typer.echo(f"Pending operations: {len(db.pending())}")


@app.command()
def search(text: Annotated[str, typer.Argument()]) -> None:
    query = text.casefold()
    for kind in ENTITY_FIELDS:
        rows = [r for r in service().list(kind) if query in str(r.data).casefold()]
        if rows:
            render(rows, kind)


@app.command("sync")
def sync_command(
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    db = service()
    if dry_run:
        rows = db.pending()
        typer.echo(f"Dry run: {len(rows)} queued operation(s)")
        return
    base_url = os.environ.get("MYCMD_API_URL")
    access_token = os.environ.get("MYCMD_ACCESS_TOKEN")
    if not base_url or not access_token:
        fail("Set MYCMD_API_URL and MYCMD_ACCESS_TOKEN before sync", 3)
    from mycmd.api_client.client import ApiClient
    from mycmd.sync.coordinator import SyncCoordinator

    result = SyncCoordinator(db, ApiClient(base_url, access_token)).run()
    typer.echo(f"Sync status: {result['status']}")
    if result.get("error"):
        fail(str(result["error"]), 3)


conflicts_app = typer.Typer(
    help="List and resolve durable synchronization conflicts.",
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


@conflicts_app.command("list")
def conflicts_list() -> None:
    db = service()
    rows = db.db.execute(
        "SELECT * FROM local_conflicts WHERE owner_id=? AND state='pending' ORDER BY created_at",
        (db.owner_id,),
    ).fetchall()
    if not rows:
        typer.echo("No pending conflicts")
        return
    for row in rows:
        typer.echo(
            f"{row['id']}  {row['entity_type']}:{row['entity_id']}  "
            f"{row['conflict_type']}  {row['state']}"
        )


@conflicts_app.command("resolve")
def conflicts_resolve(
    conflict_id: str,
    keep: str = typer.Option(..., "--keep", help="local, server, or merge"),
    merge_json: str | None = typer.Option(None, "--merge-json"),
) -> None:
    if keep not in {"local", "server", "merge"}:
        fail("Use --keep local, --keep server, or --keep merge")
    import json

    from mycmd.api_client.client import ApiClient
    from mycmd.sync.coordinator import SyncCoordinator

    base_url = os.environ.get("MYCMD_API_URL")
    access_token = os.environ.get("MYCMD_ACCESS_TOKEN")
    if not base_url or not access_token:
        fail("Set MYCMD_API_URL and MYCMD_ACCESS_TOKEN before conflict resolution", 3)
    db = service()
    coordinator = SyncCoordinator(db, ApiClient(base_url, access_token))
    try:
        if keep == "server":
            result = coordinator.resolve_keep_server(conflict_id)
        elif keep == "merge":
            if merge_json is None:
                raise ValueError("merge-json is required for --keep merge")
            merged = json.loads(merge_json)
            if not isinstance(merged, dict):
                raise ValueError("merge-json must be a JSON object")
            result = coordinator.resolve_manual_merge(conflict_id, merged)
        else:
            result = coordinator.resolve_keep_local(conflict_id)
        typer.echo(f"Conflict resolution: {result['status']}")
    except (LookupError, ValueError, json.JSONDecodeError) as exc:
        fail(str(exc), 4)


app.add_typer(conflicts_app, name="conflicts")


backup_app = typer.Typer(
    help="Create, verify and restore local SQLite backups.",
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


@backup_app.command("create")
def backup_create(
    output: str = typer.Option(..., "--output"),
    encrypt: bool = typer.Option(False, "--encrypt"),
    password_env: str = typer.Option("MYCMD_BACKUP_PASSWORD", "--password-env"),
) -> None:
    root = data_directory()
    live = root / "mycmd.sqlite3"
    if not live.is_file():
        fail(f"Local database does not exist at {live}", 3)
    backup_path = Path(output).expanduser()
    try:
        if encrypt:
            password = os.environ.get(password_env)
            if not password:
                fail(f"Set {password_env} before creating an encrypted backup", 3)
            temp = backup_path.with_suffix(backup_path.suffix + ".sqlite")
            try:
                create_sqlite_backup(live, temp, owner_id=owner_id())
                encrypt_sqlite_backup(
                    temp,
                    backup_path,
                    password=password,
                    owner_id=owner_id(),
                )
            finally:
                temp.unlink(missing_ok=True)
                _manifest_path(temp).unlink(missing_ok=True)
            typer.echo(f"Created encrypted backup {backup_path}")
        else:
            create_sqlite_backup(live, backup_path, owner_id=owner_id())
            typer.echo(f"Created backup {backup_path}")
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        fail(str(exc), 3)


@backup_app.command("list")
def backup_list(directory: str = typer.Option(".", "--directory")) -> None:
    root = Path(directory).expanduser()
    manifests = sorted(root.glob("*.manifest.json"))
    if not manifests:
        typer.echo("No backups found")
        return
    for manifest_path in manifests:
        typer.echo(str(manifest_path.with_suffix("").with_suffix("")))


@backup_app.command("verify")
def backup_verify(
    backup: str = typer.Argument(...),
    password_env: str | None = typer.Option(None, "--password-env"),
) -> None:
    backup_path = Path(backup).expanduser()
    manifest_path = _manifest_path(backup_path)
    try:
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("encrypted"):
                password = os.environ.get(password_env or "MYCMD_BACKUP_PASSWORD")
                if not password:
                    fail("Set MYCMD_BACKUP_PASSWORD before verifying an encrypted backup", 3)
                verify_encrypted_sqlite_backup(
                    backup_path,
                    password=password,
                    owner_id=owner_id(),
                )
            else:
                verify_sqlite_backup(backup_path, owner_id=owner_id())
        else:
            raise ValidationError("Backup manifest does not exist")
        typer.echo(f"Verified backup {backup_path}")
    except (OSError, ValueError, ValidationError) as exc:
        fail(str(exc), 3)


@backup_app.command("restore")
def backup_restore(
    backup: str = typer.Argument(...),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    password_env: str | None = typer.Option(None, "--password-env"),
) -> None:
    if not dry_run and not confirm:
        fail("Restore requires --confirm or use --dry-run", 4)
    root = data_directory()
    live = root / "mycmd.sqlite3"
    backup_path = Path(backup).expanduser()
    decrypted: Path | None = None
    try:
        manifest_path = _manifest_path(backup_path)
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("encrypted"):
                password = os.environ.get(password_env or "MYCMD_BACKUP_PASSWORD")
                if not password:
                    fail("Set MYCMD_BACKUP_PASSWORD before restoring an encrypted backup", 3)
                decrypted = backup_path.with_suffix(backup_path.suffix + ".decrypted")
                decrypt_sqlite_backup(
                    backup_path,
                    decrypted,
                    password=password,
                    owner_id=owner_id(),
                )
                backup_path = decrypted
        report = restore_sqlite_backup(
            live,
            backup_path,
            owner_id=owner_id(),
            dry_run=dry_run,
        )
        typer.echo(
            f"Restore {report['status']}: "
            f"{report.get('records', 0)} records, "
            f"{report.get('pending_operations', 0)} pending operations"
        )
    except (OSError, ValueError, ValidationError, sqlite3.Error) as exc:
        fail(str(exc), 3)
    finally:
        if decrypted is not None:
            decrypted.unlink(missing_ok=True)
            _manifest_path(decrypted).unlink(missing_ok=True)


app.add_typer(backup_app, name="backup")
