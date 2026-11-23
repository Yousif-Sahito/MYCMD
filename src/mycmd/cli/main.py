"""MYCMD command line interface."""

import os
import sqlite3
from collections.abc import Iterable
from typing import Annotated, NoReturn
from uuid import UUID

os.environ.setdefault("TYPER_USE_RICH", "0")
import typer

from mycmd.config import data_directory
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
