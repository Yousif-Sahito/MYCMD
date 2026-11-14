"""Shared, dependency-free domain validation for trusted local clients."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlsplit
from uuid import UUID


class ValidationError(ValueError):
    """Input does not satisfy the domain contract."""


FIELDS = {
    "projects": {
        "slug",
        "title",
        "description",
        "status",
        "technologies",
        "links",
        "started_at",
        "finished_at",
        "notes",
    },
    "skills": {"name", "category", "level", "notes"},
    "education": {"institution", "program", "status", "started_at", "ended_at", "notes"},
    "certificates": {
        "name",
        "issuer",
        "credential_id",
        "credential_url",
        "issued_at",
        "expires_at",
        "notes",
    },
    "milestones": {"title", "due_at", "priority", "status", "completed_at", "notes"},
}
REQUIRED = {
    "projects": {"slug", "title", "status"},
    "skills": {"name", "category", "level"},
    "education": {"institution", "program", "status"},
    "certificates": {"name", "issuer"},
    "milestones": {"title", "priority", "status"},
}
ENUMS = {
    ("projects", "status"): {"planned", "active", "completed", "archived"},
    ("skills", "level"): {"beginner", "intermediate", "advanced", "expert"},
    ("education", "status"): {"planned", "in_progress", "completed", "withdrawn"},
    ("milestones", "status"): {"planned", "active", "completed", "cancelled"},
    ("milestones", "priority"): {"low", "medium", "high"},
}


def uuid_text(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Expected UUID") from exc


def utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
        offset = parsed.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise ValidationError("Expected UTC timestamp") from exc
    return value


def safe_url(value: str) -> None:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError
        _ = parsed.port
    except ValueError as exc:
        raise ValidationError("Expected HTTP(S) URL without credentials") from exc


def validate(kind: str, data: dict[str, object]) -> dict[str, object]:
    if kind not in FIELDS:
        raise ValidationError("Unknown entity type")
    if data.keys() - FIELDS[kind] or REQUIRED[kind] - data.keys():
        raise ValidationError("Unknown or missing fields")
    result: dict[str, object] = {}
    for key, value in data.items():
        if value is None:
            if key in REQUIRED[kind] or key in {"technologies", "links"}:
                raise ValidationError(f"{key} cannot be null")
        elif key in {"technologies", "links"}:
            if not isinstance(value, list) or len(value) > 100:
                raise ValidationError(f"{key} must be a list of at most 100 strings")
            for item in value:
                if not isinstance(item, str) or not item.strip() or len(item) > 2048:
                    raise ValidationError(f"Invalid {key} entry")
                if key == "links":
                    safe_url(item)
            value = list(value)
        elif not isinstance(value, str):
            raise ValidationError(f"{key} must be text")
        else:
            limit = 10000 if key in {"notes", "description"} else 2048 if "url" in key else 200
            if len(value) > limit or (key in REQUIRED[kind] and not value.strip()):
                raise ValidationError(f"Invalid {key} length")
            if (kind, key) in ENUMS and value not in ENUMS[kind, key]:
                raise ValidationError(f"Invalid {key}")
            if key.endswith("_at"):
                try:
                    if date.fromisoformat(value).isoformat() != value:
                        raise ValueError
                except ValueError as exc:
                    raise ValidationError(f"{key} must be YYYY-MM-DD") from exc
            if key == "credential_url":
                safe_url(value)
            if key == "slug" and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
                raise ValidationError("Invalid slug")
        result[key] = value
    for start, end in [
        ("started_at", "finished_at"),
        ("started_at", "ended_at"),
        ("issued_at", "expires_at"),
    ]:
        a, b = result.get(start), result.get(end)
        if isinstance(a, str) and isinstance(b, str) and a > b:
            raise ValidationError(f"{end} precedes {start}")
    if kind == "milestones" and (
        (result["status"] == "completed") != bool(result.get("completed_at"))
    ):
        raise ValidationError("Completed milestones require completed_at; other states forbid it")
    return result


@dataclass(frozen=True)
class Record:
    id: str
    owner_id: str
    kind: str
    data: dict[str, object]
    created_at: str
    updated_at: str
    version: int
    deleted_at: str | None
    sync_status: str
    last_server_version: int
