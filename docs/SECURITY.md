# Security requirements and verification plan

These are required controls, not claims of implemented protection.

1. Browser input is untrusted: allowlisted commands only, deterministic quoted tokenization,
   text rendering, validated links, no arbitrary shell/SQL/filesystem dispatch.
2. Local shell startup requires explicit user action, no elevation, documented sanitized
   environment, no silent startup scripts or command replay, bounded buffers and cleanup.
3. API enforces owner scope, Argon2id hashes, rate limiting, short access tokens and revocable
   refresh sessions. Recovery policy must be documented before password login ships.
4. Keyring stores client secrets; TLS validation is mandatory. CORS uses explicit origins.
5. Public records are explicitly published. Logs redact credentials and personal payloads;
   telemetry is off by default. Logout prevents cross-account cache exposure.
6. Imports validate schema/checksum/ownership; exports exclude secrets. Restore rehearsal
   uses a separate DB. Backups require encryption and a tested retention/recovery policy.
7. CI and release gates include dependency scanning, authorization abuse tests, browser
   injection tests, terminal lifecycle tests and sync failure injection.

Open design decisions to resolve with tests: token lifetimes, refresh rotation, tombstone
retention/rebootstrap, cache logout policy and OS-specific keyring failure behavior.
