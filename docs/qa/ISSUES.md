# Phase 4 unresolved issues

No unresolved critical or high-severity implementation findings were found by the
Phase 4 source, lifecycle, security, accessibility or release reviews.

## Open platform and verification limitations

- The final pushed-SHA Windows and Ubuntu GitHub Actions run is verified at
  `58049c97e3aa5972c91d6f33a75502630e2693ce`.
- Direct Kali desktop verification has not occurred; Ubuntu CI does not establish
  Kali support.
- Visible-desktop and screen-reader verification remain distinct from the executed
  offscreen and native Windows automation evidence.
- Detached process descendants and shell-exits-first ConPTY cleanup remain outside
  the ordinary foreground-child terminal coverage.

## Phase 5 findings

No unresolved CRITICAL or HIGH security findings were found.

| ID | Severity | Reviewer | Finding | Disposition | Verification |
| --- | --- | --- | --- | --- | --- |
| P5-01 | MEDIUM | Architecture/Terminal | xterm Up/Down history could use stale React state | Fixed by using `historyRef.current` for arrow navigation | Unit/E2E source review |
| P5-02 | MEDIUM | Architecture | Terminal font setting was stored but not applied | Fixed by reading the persisted font size in xterm initialization | Typecheck/build pass |
| P5-03 | LOW | Architecture | Printable paste could contain multiple characters | Fixed by handling multi-character printable input | Playwright pass |
| P5-04 | HIGH | Accessibility | Light-theme primary and completed text contrast could be insufficient | Fixed with white primary text and darker completed badge text | Exact-SHA CI pass; axe/Playwright pass |
| P5-05 | MEDIUM | Public Data | Public URL policy accepted HTTP/private/credential URLs | Fixed to require HTTPS and reject credentials/private hosts | Public-data unit tests |
| P5-06 | MEDIUM | Public Data | Public data schema validated only project slugs/URLs | Expanded profile URL validation and project data checks | Public-data unit tests |
| P5-07 | MEDIUM | Accessibility | Terminal lacked an assistive fallback/description | Added `aria-describedby` and accessible visually-hidden/mobile fallback | Playwright pass |
| P5-08 | LOW | Release | CI omitted dist artifact upload | Added `apps/portfolio/dist` upload | Workflow source review |

## Final Phase 5 disposition

No unresolved CRITICAL or HIGH findings remain. Final exact-SHA GitHub Actions
run `45298690921` passed all four matrix jobs.

## Phase 6 verification

- Docker CLI was unavailable locally; Docker Compose was verified by the Ubuntu
  GitHub Actions MySQL service-container job.
- Real MySQL migration and API tests passed in exact-SHA CI.
- No CRITICAL or HIGH Phase 6 security finding is currently recorded.
- Phase 6 API route closures now bind kind explicitly; no client `kind_name` override remains.
- Refresh sessions use `SELECT ... FOR UPDATE`; record CRUD uses `SELECT ... FOR UPDATE`.
- Logout verifies the refresh session belongs to the authenticated user.
- Bootstrap remains application-level and needs a singleton invariant before real multi-owner release.
## Final Phase 6 disposition

Exact-SHA run `45347902966` passed the MySQL job, both Python jobs and both
portfolio jobs. No unresolved CRITICAL or HIGH Phase 6 findings remain.

## Phase 7 completion recovery

- Manual keep-server, keep-local and manual-merge resolution code is implemented.
- Unit tests verify invalid merge rejection, version-checked merge queueing and
  explicit keep-server resolution.
- Real-MySQL test coverage is present in `test_mysql_server.py`, but local execution
  is skipped without `MYCMD_MYSQL_TEST_URL`.
- Docker CLI is unavailable locally, and Kali-specific validation remains unperformed.

## Final Phase 7 disposition

Exact-SHA run `45457324606` passed Windows and Ubuntu Python jobs, both portfolio jobs,
and the MySQL 8.4 migration/API job at SHA `7c84dda230ea61b9b0a35d2f4439c7c2606b2dc5`.
Final documentation SHA `d24c1a206821ca2e1acd6a884f7a0c250d43bbd6` passed its exact-SHA
CI run `45459313500`.
No unresolved CRITICAL or HIGH Phase 7 findings remain. Kali-specific validation remains
unverified and must not be represented as direct Kali compatibility evidence.

## Final Phase 8 disposition

The Phase 8 baseline added executable backup, restore-failure and 10,000-record
performance coverage. Repository-wide lint, strict mypy, dependency audit,
local tests, offline build and exact-SHA Windows, Ubuntu, portfolio and MySQL
CI are passing. Kali-specific GUI/terminal verification remains unperformed.

## Phase 9 packaging

PyInstaller OS-specific desktop executable support is verified on Windows and Ubuntu
exact-SHA CI. A real Windows `MYCMD.exe` build completed and stayed alive for a
12-second offscreen GUI smoke. Direct Kali installer and clean-machine verification
remain pending.

## Phase 10 deployment disposition

Production configuration now rejects SQLite and HTTP public origins. Deployment
Docker/Caddy assets and encrypted MySQL backup/migration rehearsal helpers are
implemented. Exact-SHA run `45696421788` passed Windows, Ubuntu, portfolio and
MySQL CI. Public DNS/ACME, real disposable MySQL backup/restore and Docker hosting
evidence remain external blockers. No public deployment claim is made.
