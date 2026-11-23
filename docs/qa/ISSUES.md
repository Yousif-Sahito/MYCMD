# Phase 4 unresolved issues

No unresolved critical or high-severity implementation findings were found by the
Phase 4 source, lifecycle, security, accessibility or release reviews.

## Open platform and verification limitations

- The final pushed-SHA Windows and Ubuntu GitHub Actions run is verified at
  `0f8f1a5cf1ed70a34950301611a45c7b22a1b08a`.
- Direct Kali desktop verification has not occurred; Ubuntu CI does not establish
  Kali support.
- Visible-desktop and screen-reader verification remain distinct from the executed
  offscreen and native Windows automation evidence.
- Detached process descendants and shell-exits-first ConPTY cleanup remain outside
  the ordinary foreground-child terminal coverage.
