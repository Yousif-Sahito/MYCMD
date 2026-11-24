from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_payload(
    code: str, message: str, request_id: str, field_errors: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "field_errors": field_errors or {},
        "request_id": request_id,
    }


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        429: "rate_limited",
    }
    code = codes.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, str(exc.detail), get_request_id(request)),
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    field_errors: dict[str, list[str]] = {}
    for item in exc.errors():
        location = ".".join(str(part) for part in item["loc"])
        field_errors.setdefault(location, []).append(str(item["msg"]))
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "validation_error",
            "Request validation failed",
            get_request_id(request),
            field_errors,
        ),
    )
