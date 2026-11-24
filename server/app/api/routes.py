from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.app.auth_service import AuthService
from server.app.db.models import Record, User
from server.app.db.repositories import RecordRepository
from server.app.db.sync_repository import SyncRepository
from server.app.dependencies import current_user, get_db
from server.app.schemas import (
    BootstrapRequest,
    LoginRequest,
    PageResponse,
    RecordCreate,
    RecordResponse,
    RecordUpdate,
    RefreshRequest,
    SyncOperationResult,
    SyncPullItem,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1")
limiter = Limiter(key_func=get_remote_address)


@router.post("/auth/bootstrap", status_code=201)
@limiter.limit("5/ minute")
async def bootstrap(
    request: Request,
    body: BootstrapRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        user = AuthService(db, request.app.state.settings).bootstrap(
            body.email, body.password, body.bootstrap_token
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse(
        id=UUID(user.id),
        email=user.email,
        status=user.status,
        created_at=user.created_at.isoformat(),
    )


@router.post("/auth/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user, access, refresh = AuthService(db, request.app.state.settings).login(
            body.email, body.password
        )
    except LookupError as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh")
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user, access, refresh = AuthService(db, request.app.state.settings).refresh(
            body.refresh_token
        )
    except LookupError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    body: RefreshRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    auth = AuthService(db, request.app.state.settings)
    try:
        auth.revoke_for_user(user.id, body.refresh_token)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/me")
async def me(
    user: User = Depends(current_user),
) -> UserResponse:
    return UserResponse(
        id=UUID(user.id),
        email=user.email,
        status=user.status,
        created_at=user.created_at.isoformat(),
    )


def record_response(record: Record) -> RecordResponse:
    return RecordResponse(
        id=UUID(record.id),
        kind=record.kind,
        data=record.data,
        created_at=record.created_at,
        updated_at=record.updated_at,
        version=record.version,
        deleted_at=record.deleted_at.isoformat() if record.deleted_at else None,
    )


def _entity_router(kind: str) -> APIRouter:
    entity = APIRouter(prefix=f"/{kind}")

    @entity.get("")
    async def list_records(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        search: str | None = Query(default=None, max_length=200),
        status_filter: str | None = Query(default=None, alias="status", max_length=32),
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> PageResponse:
        rows, total = RecordRepository(db).list(
            user.id,
            kind,
            page=page,
            page_size=page_size,
            search=search,
            status=status_filter,
        )
        return PageResponse(
            items=[record_response(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    @entity.post("", status_code=201)
    async def create_record(
        body: RecordCreate,
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> RecordResponse:
        try:
            record = RecordRepository(db).create(user.id, kind, body.data)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return record_response(record)

    @entity.get("/{record_id}")
    async def get_record(
        record_id: str,
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> RecordResponse:
        record = RecordRepository(db).get(user.id, kind, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return record_response(record)

    @entity.patch("/{record_id}")
    async def update_record(
        record_id: str,
        body: RecordUpdate,
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> RecordResponse:
        try:
            record = RecordRepository(db).update(
                user.id, kind, record_id, body.expected_version, body.data
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Record not found") from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return record_response(record)

    @entity.delete("/{record_id}", status_code=204)
    async def delete_record(
        record_id: str,
        expected_version: int = Query(ge=1),
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> None:
        try:
            RecordRepository(db).delete(user.id, kind, record_id, expected_version)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Record not found") from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return entity


def kind_routes(kind: str) -> tuple[APIRouter, str]:
    entity = APIRouter(prefix=f"/{kind}")
    return entity, kind


def register_entity_routes() -> APIRouter:
    api = APIRouter()
    for kind in ("projects", "skills", "education", "certificates", "milestones"):
        api.include_router(_entity_router(kind))
    return api


router.include_router(register_entity_routes())


@router.post("/sync/push")
async def sync_push(
    body: SyncPushRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> SyncPushResponse:
    operations = [operation.model_dump(mode="json") for operation in body.operations]
    try:
        results = SyncRepository(db).push(user.id, operations)
    except (ValueError, IntegrityError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SyncPushResponse(results=[SyncOperationResult.model_validate(row) for row in results])


@router.get("/sync/pull")
async def sync_pull(
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> SyncPullResponse:
    rows, next_cursor = SyncRepository(db).pull(user.id, cursor, limit)
    items: list[SyncPullItem] = []
    for row in rows:
        record = None
        if not row.tombstone and row.record_json is not None:
            record = RecordResponse.model_validate(row.record_json)
        items.append(
            SyncPullItem(
                sequence=row.sequence,
                entity_type=row.entity_type,
                entity_id=UUID(row.entity_id),
                version=row.version,
                changed_at=row.changed_at,
                tombstone=row.tombstone,
                record=record,
            )
        )
    return SyncPullResponse(items=items, next_cursor=next_cursor)


@router.get("/public/portfolio")
@limiter.limit("60/minute")
async def public_portfolio(request: Request) -> dict[str, Any]:
    return {
        "profile": {
            "name": "MYCMD",
            "heading": "An offline-first personal command centre",
            "introduction": "A curated public overview of the MYCMD project.",
            "github": "https://github.com/Yousif-Sahito/MYCMD",
        },
        "projects": [
            {
                "slug": "mycmd-cli",
                "title": "MYCMD CLI",
                "status": "completed",
                "technologies": ["Python", "Typer", "Rich", "SQLite"],
            },
            {
                "slug": "mycmd-terminal",
                "title": "MYCMD Terminal Engine",
                "status": "completed",
                "technologies": ["Python", "ConPTY", "POSIX PTY"],
            },
            {
                "slug": "mycmd-desktop",
                "title": "MYCMD Desktop",
                "status": "completed",
                "technologies": ["PySide6", "Qt WebEngine", "xterm.js"],
            },
            {
                "slug": "mycmd-portfolio",
                "title": "MYCMD Public Portfolio",
                "status": "active",
                "technologies": ["React", "TypeScript", "Vite", "xterm.js"],
            },
        ],
        "skills": [],
        "education": [],
        "certificates": [],
        "milestones": [],
        "source": "curated-public",
    }
