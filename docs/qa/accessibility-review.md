# Accessibility and UX review

Reviewer: actual delegated `qa_release` agent. Examined main window, entity pages,
forms, preferences and native Windows captures; authored and executed real Qt tests.

## Actual automated checks

- Sidebar Down key changes selected page and displayed page.
- Tab moves from theme to terminal font-size control; Shift+Tab returns to theme.
- Enter on form Save validates an empty project, displays a named error label and
  keeps the dialog open. Escape dismisses an unchanged form.
- Navigation, settings, search, filter, tables and form inputs have accessible names.
- Light/dark preferences apply and persist; a focus stylesheet exists, and native
  captures visibly show focused controls.
- Native Windows small/medium/maximized layouts captured; form scrolling preserves
  Save/Cancel visibility. Native display scaling observed at 125%.

Native five-test navigation/accessibility batch: **5 passed in 6.81s**. Added native
project form/theme/error capture test: **1 passed in 2.24s**. Full release results
must be read from the final executed QA report, not inferred from these subsets.

## Findings

| ID | Severity | Component | Reproduction | Resolution and evidence |
| --- | --- | --- | --- | --- |
| ACCESS-01 | HIGH | Dark table headers | Open Projects in dark theme on native Windows; header background white with near-white text, Status / Category clipped. | Lead styled QHeaderView sections and widened columns; inspected updated populated-projects.png with readable full headings. Resolved for native captured state. |
| ACCESS-02 | INFORMATIONAL | Offscreen font environment | Run Windows offscreen capture; glyphs render as boxes. | Use native desktop rendering for visual evidence. Offscreen execution remains functional evidence only. |

## Limitations

Accessible names and keyboard subset tests do not establish full accessibility.
No screen-reader session, localization review, independent contrast-meter audit,
or direct Kali desktop run has occurred. 125% native scaling was observed; separate
200% scaling and increased system text-size verification remain to be recorded.
Terminal keyboard escape/focus, clipboard and scrollback behavior require terminal
integration evidence. No claim of universal accessibility compliance is made.
