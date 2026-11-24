"""Real Qt navigation, settings, persistence and visible widget snapshots."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox, QPushButton

from mycmd.gui.forms import RecordDialog
from mycmd.gui.main_window import MainWindow
from mycmd.gui.settings import Preferences


@pytest.fixture
def navigation_window(qtbot, tmp_path):
    window = MainWindow(root=tmp_path)
    # This window closes asynchronously. pytest-qt's addWidget teardown calls
    # deleteLater before fixture finalizers, preventing its close timer running.
    window.show()
    qtbot.waitUntil(lambda: window.ready, timeout=15000)
    yield window
    window.close()
    qtbot.waitUntil(lambda: window.closed, timeout=15000)
    window.deleteLater()


def test_navigation_all_pages_and_empty_counts(qtbot, navigation_window):
    window = navigation_window
    assert window.navigation.count() == 9
    for kind in window.entities:
        assert f"{kind.title()}: 0" in window.dashboard.text()
    assert "Pending operations: 0" in window.dashboard.text()
    for index in range(window.navigation.count()):
        rectangle = window.navigation.visualItemRect(window.navigation.item(index))
        qtbot.mouseClick(
            window.navigation.viewport(), Qt.MouseButton.LeftButton, pos=rectangle.center()
        )
        assert window.stack.currentIndex() == index
        assert window.stack.currentWidget().isVisible()
    assert "not implemented" in window.sync.text()
    assert "No last-sync timestamp" in window.sync.text()


def test_settings_saved_by_button_and_reloaded(qtbot, navigation_window, tmp_path):
    window = navigation_window
    window.navigation.setCurrentRow(8)
    window.theme.setCurrentText("light")
    window.font_size.setValue(19)
    window.scrollback.setValue(7500)
    window.cwd.setText(str(tmp_path))
    save = next(
        button
        for button in window.stack.currentWidget().findChildren(QPushButton)
        if button.text() == "Save preferences"
    )
    qtbot.mouseClick(save, Qt.MouseButton.LeftButton)
    saved = Preferences.load(tmp_path)
    assert saved.theme == "light"
    assert saved.font_size == 19
    assert saved.scrollback == 7500
    assert saved.cwd == str(tmp_path)
    assert window.terminal.preferences == saved
    window.close()
    qtbot.waitUntil(lambda: window.closed, timeout=15000)
    reopened = MainWindow(root=tmp_path)
    qtbot.addWidget(reopened)
    reopened.show()
    try:
        qtbot.waitUntil(lambda: reopened.ready, timeout=15000)
        assert reopened.preferences == saved
        assert reopened.theme.currentText() == "light"
    finally:
        reopened.close()
        qtbot.waitUntil(lambda: reopened.closed, timeout=15000)


def test_navigation_resize_and_capture(qtbot, navigation_window):
    window = navigation_window
    output = Path(".tools/phase4-visual")
    output.mkdir(parents=True, exist_ok=True)
    for name, width, height, index in [
        ("dashboard", 1100, 720, 0),
        ("empty-projects", 1100, 720, 2),
        ("small-projects", 720, 480, 2),
        ("small-settings", 720, 480, 8),
        ("medium-settings", 1100, 720, 8),
    ]:
        window.resize(width, height)
        window.navigation.setCurrentRow(index)
        qtbot.wait(100)
        assert window.navigation.isVisible()
        assert window.stack.currentWidget().isVisible()
        assert window.grab().save(str(output / f"{name}.png"))
    window.showMaximized()
    qtbot.wait(100)
    assert window.grab().save(str(output / "maximized-settings.png"))


def test_navigation_form_and_theme_screenshots(qtbot, navigation_window):
    window = navigation_window
    output = Path(".tools/phase4-visual")
    output.mkdir(parents=True, exist_ok=True)
    window.navigation.setCurrentRow(2)
    page = window.entities["projects"]
    create = next(button for button in page.findChildren(QPushButton) if button.text() == "Create")
    qtbot.mouseClick(create, Qt.MouseButton.LeftButton)
    dialog = page.findChild(RecordDialog)
    assert dialog is not None
    qtbot.wait(100)
    assert dialog.grab().save(str(output / "create-project.png"))
    dialog.fields["slug"].setText("visual-review")
    dialog.fields["title"].setText("Visual review project")
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(
        lambda: (
            page.table.rowCount() == 1
            and page.table.item(0, 0) is not None
            and page.table.item(0, 0).text() == "Visual review project"
        ),
        timeout=30000,
    )
    assert window.grab().save(str(output / "populated-projects.png"))
    page.table.selectRow(0)
    page.edit()
    qtbot.wait(100)
    edit = next(item for item in page.findChildren(RecordDialog) if item.isVisible())
    assert edit.grab().save(str(output / "edit-project.png"))
    qtbot.keyClick(edit, Qt.Key.Key_Escape)
    window.navigation.setCurrentRow(8)
    for theme in ("dark", "light"):
        window.theme.setCurrentText(theme)
        window.save_preferences()
        qtbot.wait(100)
        assert window.grab().save(str(output / f"settings-{theme}.png"))
    captured = []

    def capture_error():
        message = QApplication.activeModalWidget()
        if isinstance(message, QMessageBox):
            captured.append(message.grab().save(str(output / "error-dialog.png")))
            message.accept()

    QTimer.singleShot(100, capture_error)
    window.show_error("Review test: a local operation could not be completed.")
    assert captured == [True]
