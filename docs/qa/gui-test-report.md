# GUI functional review

Reviewer: real delegated `qa_release` agent, independently inspecting implemented
`main_window.py`, `entities.py`, `forms.py`, `controller.py`, `settings.py`,
`terminal.py`, and the installed-smoke API.

## Executed checks

`tests/gui/test_navigation.py` exercises actual Qt mouse navigation through all nine
pages, empty dashboard counts, honest Sync text, settings Save button, preference
file reload and window restart, window resizing, real project creation through the
form, edit dialog opening, theme switching and the application's error dialog.

`tests/gui/test_accessibility.py` exercises keyboard navigation, focus, form
validation and Escape dismissal. All databases/preferences use pytest temporary
directories. No personal database was opened.

Windows 10, Python 3.13.12, PySide6/Qt 6.12.0:

- Initial five-test offscreen run: **5 passed, 2 teardown errors**. Root cause was
  the review fixture registering an asynchronous-close window with pytest-qt's
  automatic deleteLater cleanup, which executes before fixture finalizers.
  Fixed fixture to own close/wait/deleteLater. Rerun: **5 passed in 8.26s**.
- Native Windows desktop rerun (no offscreen platform): **5 passed in 6.81s**.
- Added real form/theme/error screenshot test; initial stale `page.create()` call
  hit QWidget.create after production renamed the action. Fixed test to click the
  actual Create button. Targeted native rerun: **1 passed in 2.24s**.

These are exact historical results, not a claim that the final complete suite or
Linux CI has passed. The lead's final gate report supplies final aggregate counts.

## Visual inspection

Actual Qt widget captures are generated in ignored `.tools/phase4-visual/`, not
committed. Native captures used the Windows display at 1.25 device pixel ratio:
1100x720 logical window captured as 1375x900 physical pixels. Inspected dashboard,
empty/populated Projects, small Settings, create Project, light Settings and error
dialog. Text and primary actions are visible, and the create form scrolls while
Save/Cancel remain available. Dark/light focus treatment is visible.

Found dark table header text effectively white-on-white and a clipped Status /
Category heading (ACCESS-01). Lead added explicit header styling and wider columns;
subsequent populated screenshot confirms readable full headings.

Offscreen captures initially rendered glyphs as boxes, so they were not accepted
as visual proof. Native captures replaced them after actual desktop execution.

## Remaining scope

Terminal execution, full five-entity CRUD, destructive confirmation, search/filter,
concurrent edits and installed-package evidence belong to other executable tests
and consolidated evidence. This report alone does not certify those behaviors.
Direct Kali testing and manual screen-reader validation have not occurred.
