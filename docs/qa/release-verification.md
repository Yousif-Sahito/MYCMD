# Phase 4 CI and release review

Reviewer: independently delegated `qa_release` subagent. Initial review only;
Phase 4 release is **NOT VERIFIED**.

## Files inspected

- `pyproject.toml`, `.github/workflows/ci.yml`, `.gitignore`.
- `scripts/check_wheel.py`, `scripts/check_installed_wheel.py`.
- Existing test paths and the Phase 4 engineering contract.

## Findings

| ID | Severity | Component | Finding | Status |
| --- | --- | --- | --- | --- |
| RELEASE-01 | HIGH | Installed smoke | Existing clean-wheel verification covers CLI and PTY but does not install desktop extras or launch the GUI. | Open pending implementation |
| RELEASE-02 | HIGH | CI | Existing Windows/Ubuntu workflow has no GUI dependencies, virtual display or installed GUI check. | Open pending implementation |
| RELEASE-03 | INFORMATIONAL | User changes | Existing README and gitignore edits and phase3-test-tmp are outside reviewer ownership; preserved. | Preserved |

## Reproducible gate workflow

`python scripts/qa/run_all.py --local` executes actual commands, retains logs and
exit codes under `.tools/phase4-qa`, and writes JSON and Markdown reports. Missing
tests, missing tools, failed commands and missing artifacts cannot pass. A local
result cannot establish CI verification. Without `--local`, `--ci-run RUN_ID` is
required for a passing release result; the runner fetches GitHub evidence and
requires the exact HEAD SHA and successful Windows and Ubuntu jobs.

Planned acceptance execution: frozen dependency install; lock and dependency
checks; Ruff formatting/lint; strict mypy; unit, storage, CLI, terminal, GUI,
accessibility and security tests; sdist/wheel build; resource inspection; clean
installed GUI launch; Git whitespace/hygiene review; exact-commit CI inspection.
The automatic whitespace check complements, and does not replace, manual staged
diff, secret and unrelated-edit review by the lead engineer.

## Actual execution evidence

Executed Ruff format and lint on `scripts/qa`: passed. Executed runner behavioral
probes using actual subprocesses: exit zero produces PASS; exit three preserves
the failing exit code; a nonexistent executable produces BLOCKED; a one-second
timeout terminates the test subprocess and produces BLOCKED. Missing CI evidence
is mandatory in release mode and nonmandatory only with explicit `--local`.
The runner also parses pytest JUnit results and rejects all-skipped groups.

No Phase 4 build, installed GUI launch or new GitHub CI run has yet been executed
by this reviewer. Do not interpret runner verification as application verification.

## Platform limitations

Offscreen or Xvfb GUI execution is distinct from a visible Windows desktop visual
review. Ubuntu CI does not establish direct Kali testing. Final evidence must
identify display mode, commit, run URL and actual test counts.
