# 5. Security Review

## Scope

The pass reviewed authentication, owner scope, CORS, TLS configuration,
browser terminal restrictions, backup encryption, terminal bridges and
dependency state.

## Dependency result

`uv audit` found no known vulnerabilities across 65 packages.

## Security finding table

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| No findings | — | — | — | No unresolved security vulnerability was identified in the reviewed scope | — |

## Verified controls

- API private routes use authenticated owner identity.
- Refresh tokens are stored as hashes.
- Bootstrap and signing keys are validated in production settings.
- CORS rejects wildcard origins and production origins must use HTTPS.
- Browser terminal has no subprocess or SQL bridge.
- Terminal output is transported as data rather than inserted HTML.
- Backup passwords are not stored in backup JSON envelopes.
- MySQL CLI backup passwords are passed through `MYSQL_PWD`, not command arguments.
- No known dependency vulnerabilities were found.

## Remaining limitations

- Live TLS/ACME and public infrastructure were not tested.
- Real external secret-manager/keyring recovery was not performed.
- Direct Kali security behavior was not tested.
