# Phase 6 API review

5 API tests passed locally and 2 real-MySQL tests are skipped without a disposable URL.
Health, OpenAPI, public portfolio, auth, CRUD, stale revisions, soft deletion,
malformed JSON and CORS behavior are covered. Entity routes bind their kind inside
a route factory; no client kind override remains. Sync endpoints are absent.
