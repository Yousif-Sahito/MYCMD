# Phase 6 architecture review

Status: implementation review in progress.

The server uses FastAPI route, dependency, service/repository and SQLAlchemy boundaries.
Private and public routes are separated in `server/app/api/routes.py`; SQLite remains
outside the server production path. Real MySQL integration is represented by the
disposable MySQL test URL and Docker/CI service container. Phase 7 sync endpoints
are intentionally not implemented.
