# Phase 4 execution plan

Status: LOCAL IMPLEMENTATION AND VERIFICATION COMPLETE; EXACT-SHA CI PENDING.

1. Inspect all blueprint pages, existing code/configuration and baseline verification.
2. Add optional PySide6 desktop dependencies and locally bundled xterm.js with licenses.
3. Extract shared client configuration; implement thread-owned service controller,
   validated entity dialogs, searchable/filterable lists and live dashboard.
4. Implement settings/themes, truthful offline sync, notifications and lifecycle handling.
5. Integrate trusted local WebEngine renderer with Phase 3 session, bounded transport,
   asynchronous lifecycle, input, resize, scrollback and clipboard controls.
6. Implement Qt CRUD/restart/terminal end-to-end, security and accessibility checks.
7. Execute eight independent review responsibilities using delegated sessions (three
   concurrent reviewers available), resolve issues and capture actual visual evidence.
8. Run reproducible gates, build/inspect/install wheel, extend Windows/Ubuntu CI.
9. Review explicit staged changes, commit/push and repair exact-revision CI until green.

No production schema changes or Phase 5 work are planned. Existing README/.gitignore
edits and phase3-test-tmp are preserved. CLI-only installations retain lazy Qt imports.
Offscreen checks will not be described as visible desktop or Kali verification.
