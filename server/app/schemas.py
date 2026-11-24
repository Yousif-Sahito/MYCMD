from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class LoginRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=1024)


class RefreshRequest(APIModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class BootstrapRequest(APIModel):
    bootstrap_token: str = Field(min_length=16, max_length=256)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=1024)


class TokenResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessResponse(APIModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(APIModel):
    id: UUID
    email: str
    status: str
    created_at: str


class ProjectCreate(APIModel):
    slug: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["planned", "active", "completed", "archived"] = "planned"
    technologies: list[str] = Field(default_factory=list, max_length=100)
    links: list[str] = Field(default_factory=list, max_length=100)
    started_at: date | None = None
    finished_at: date | None = None
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("Invalid slug")
        return value


class ProjectUpdate(APIModel):
    expected_version: int = Field(ge=1)
    data: dict[str, Any]


class RecordCreate(APIModel):
    data: dict[str, Any]


class RecordUpdate(APIModel):
    expected_version: int = Field(ge=1)
    data: dict[str, Any]


class RecordResponse(APIModel):
    id: UUID
    kind: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int
    deleted_at: str | None = None


class PageResponse(APIModel):
    items: list[RecordResponse]
    page: int
    page_size: int
    total: int


class SyncOperationRequest(APIModel):
    operation_id: UUID
    device_id: UUID
    entity_type: Literal["projects", "skills", "education", "certificates", "milestones"]
    entity_id: UUID
    action: Literal["create", "update", "delete"]
    base_version: int = Field(ge=0)
    payload: dict[str, Any]


class SyncPushRequest(APIModel):
    operations: list[SyncOperationRequest] = Field(min_length=1, max_length=100)


class SyncOperationResult(APIModel):
    operation_id: UUID
    status: Literal["accepted", "conflict", "rejected"]
    record: RecordResponse | None = None
    server_record: RecordResponse | None = None
    error: str | None = None


class SyncPushResponse(APIModel):
    results: list[SyncOperationResult]


class SyncPullItem(APIModel):
    sequence: int
    entity_type: str
    entity_id: UUID
    version: int
    changed_at: datetime
    tombstone: bool
    record: RecordResponse | None = None


class SyncPullResponse(APIModel):
    items: list[SyncPullItem]
    next_cursor: int
