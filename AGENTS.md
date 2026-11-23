# MYCMD engineering instructions

Read the complete approved blueprint and current progress before architectural changes.
Phase 4 is the local PySide6 desktop only; do not begin Phase 5 without authorization.
CLI and GUI share core validation, Service and SQLite storage. Widgets must not issue SQL.
Create SQLite connections on their owning worker thread. Use the Phase 3 TerminalSession;
never emulate shell commands. Keep blocking I/O and lifecycle operations off Qt's UI thread.
Bundle terminal assets; expose no network shell or remote-page bridge. Never elevate,
log terminal input, disable TLS validation, or test against personal databases.

Preserve unrelated user changes, especially README.md and .gitignore. Inspect temporary
directories before cleanup; do not delete unknown files. Stage explicit reviewed paths.
No force push, history rewriting, credentials, databases or generated test artifacts.

Use typed modular Python, Ruff formatting/lint, strict mypy and executable tests.
The lead owns production integration; delegate independent architecture, code, GUI,
terminal, database, security, accessibility and release reviews with explicit file ownership.
Real delegated reviews must be distinguished from automated scripts and manual checklists.
Record findings and actual verification in docs/qa; consolidate issues in ISSUES.md.

Release requires real CRUD/restart/CLI interoperability, real terminal input/rendering/
resize/interrupt/cleanup, all pages/settings/themes, GUI automation, package builds and
clean installed GUI smoke. All local mandatory checks precede a normal push to main.
Inspect exact-SHA Windows and Ubuntu CI and repair failures. Pending, skipped, offscreen
and untested Kali results must be labelled honestly. No completion with mandatory failures
or unresolved critical/high findings. Final documentation commit also requires CI.
