"""Authenticated MYCMD API client for synchronization."""

from collections.abc import Mapping
from typing import Any

import httpx


class ApiError(RuntimeError):
    def __init__(self, category: str, message: str, status: int | None = None):
        super().__init__(message)
        self.category = category
        self.status = status


class ApiClient:
    def __init__(self, base_url: str, access_token: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def push(self, operations: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/sync/push", json={"operations": operations})

    def pull(self, cursor: int, limit: int = 100) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v1/sync/pull",
            params={"cursor": cursor, "limit": limit},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=dict(json) if json is not None else None,
                params=dict(params) if params is not None else None,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise ApiError("timeout", "The sync server timed out") from exc
        except httpx.RequestError as exc:
            raise ApiError("network", "Unable to reach the sync server") from exc
        if response.status_code == 401:
            raise ApiError("auth_required", "Authentication is required", 401)
        if response.status_code == 429:
            raise ApiError("retry_wait", "Sync rate limited", 429)
        if response.status_code >= 500:
            raise ApiError(
                "transient", "Sync server is temporarily unavailable", response.status_code
            )
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "Sync request failed")
            except ValueError:
                detail = "Sync request failed"
            raise ApiError("permanent", str(detail), response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError("invalid_response", "Sync server returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ApiError("invalid_response", "Sync server returned an invalid response")
        return payload
