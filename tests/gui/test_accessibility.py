"""Automated keyboard and accessible-name checks, not screen-reader certification."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit

from mycmd.gui.forms import RecordDialog
from mycmd.gui.main_window import MainWindow


def test_accessibility_navigation_and_settings_focus(qtbot, tmp_path):
    window = MainWindow(root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    try:
        qtbot.waitUntil(lambda: window.ready, timeout=15000)
        window.navigation.setFocus()
        window.navigation.setCurrentRow(0)
        qtbot.keyClick(window.navigation, Qt.Key.Key_Down)
        assert window.navigation.currentRow() == 1
        assert window.stack.currentIndex() == 1
        window.navigation.setCurrentRow(8)
        window.theme.setFocus()
        qtbot.keyClick(window.theme, Qt.Key.Key_Tab)
        assert QApplication.focusWidget() in (window.font_size, window.font_size.lineEdit())
        qtbot.keyClick(window.font_size, Qt.Key.Key_Backtab)
        assert QApplication.focusWidget() == window.theme
        for widget in (
            window.navigation,
            window.theme,
            window.font_size,
            window.scrollback,
            window.preferred_shell,
            window.cwd,
        ):
            assert widget.accessibleName()
        for page in window.entities.values():
            assert page.search.accessibleName()
            assert page.filter.accessibleName()
            assert page.table.accessibleName()
        for theme in ("light", "dark"):
            window.theme.setCurrentText(theme)
            window.save_preferences()
            assert window.preferences.theme == theme
            assert ":focus" in QApplication.instance().styleSheet()
    finally:
        window.close()
        qtbot.waitUntil(lambda: window.closed, timeout=15000)


def test_accessibility_form_labels_validation_and_escape(qtbot, tmp_path):
    window = MainWindow(root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    try:
        qtbot.waitUntil(lambda: window.ready, timeout=15000)
        dialog = RecordDialog("projects", window.controller, parent=window)
        qtbot.addWidget(dialog)
        dialog.show()
        for field in dialog.fields.values():
            assert field.accessibleName()
        save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setFocus()
        qtbot.keyClick(save, Qt.Key.Key_Return)
        assert dialog.error.text()
        assert dialog.error.accessibleName() == "Form error"
        assert dialog.isVisible()
        assert isinstance(dialog.fields["title"], QLineEdit)
        qtbot.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:
        window.close()
        qtbot.waitUntil(lambda: window.closed, timeout=15000)
