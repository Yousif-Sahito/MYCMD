# Phase 4 unresolved issues

No unresolved critical or high-severity implementation findings were found by the
Phase 4 source, lifecycle, security, accessibility or release reviews.

## Open platform and verification limitations

- Windows and Ubuntu GitHub Actions have not yet established the final pushed-SHA
  Phase 4 run in this session.
- Direct Kali desktop verification has not occurred; Ubuntu CI does not establish
  Kali support.
- Visible-desktop and screen-reader verification remain distinct from the executed
  offscreen and native Windows automation evidence.
- Detached process descendants and shell-exits-first ConPTY cleanup remain outside
  the ordinary foreground-child terminal coverage.
