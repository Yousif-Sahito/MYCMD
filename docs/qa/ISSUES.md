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
