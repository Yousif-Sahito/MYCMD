"""Real widget/service/SQLite integration using isolated personal workspaces."""

import os
import subprocess
import sys
from contextlib import closing

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
)

from mycmd.config import owner_id
from mycmd.core.service import Service
from mycmd.gui.forms import RecordDialog
from mycmd.gui.main_window import MainWindow
from mycmd.storage.database import connect

EXAMPLES = {
    "projects": {"slug": "gui-project", "title": "GUI project", "status": "active"},
    "skills": {"name": "Python", "category": "Language", "level": "advanced"},
    "education": {"institution": "University", "program": "Computing", "status": "completed"},
    "certificates": {"name": "Certificate", "issuer": "Issuer"},
    "milestones": {"title": "Ship", "priority": "high", "status": "active"},
}


@pytest.fixture
def window(qtbot, tmp_path):
    instance = MainWindow(root=tmp_path)

    def close_window(widget):
        widget.close()
        qtbot.waitUntil(lambda: widget.closed, timeout=15000)

    qtbot.addWidget(instance, before_close_func=close_window)
    instance.show()
    qtbot.waitUntil(lambda: instance.ready, timeout=15000)
    yield instance


def button(widget, title):
    return next(b for b in widget.findChildren(QPushButton) if b.text() == title)


def fill(dialog, data):
    for key, value in data.items():
        field = dialog.fields[key]
        if isinstance(field, QComboBox):
            field.setCurrentText(value)
        elif isinstance(field, QPlainTextEdit):
            field.setPlainText(value)
        else:
            field.setText(value)


def save(qtbot, dialog):
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(lambda: not dialog.isVisible(), timeout=10000)


def dialog_for(page):
    return next(d for d in page.findChildren(RecordDialog) if d.isVisible())


@pytest.mark.parametrize("kind", EXAMPLES)
def test_real_widget_crud_search_filter_and_delete(qtbot, window, tmp_path, kind):
    page = window.entities[kind]
    window.navigation.setCurrentRow(list(window.entities).index(kind) + 2)
    qtbot.waitUntil(lambda: not window.controller.pending)
    assert page.table.rowCount() == 0
    qtbot.mouseClick(button(page, "Create"), Qt.MouseButton.LeftButton)
    dialog = dialog_for(page)
    # Keep Python wrapper alive after WA_DeleteOnClose by checking page state instead.
    fill(dialog, EXAMPLES[kind])
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(lambda: len(page.records) == 1, timeout=15000)
    record_id = page.records[0].id
    assert page.records[0].data.items() >= EXAMPLES[kind].items()
    qtbot.waitUntil(lambda: f"{kind.title()}: 1" in window.dashboard.text(), timeout=15000)
    page.search.setText("nonexistent-query")
    assert page.table.rowCount() == 0
    assert page.empty.text() == "No matching records."
    page.search.clear()
    assert page.table.rowCount() == 1
    selected = next(
        EXAMPLES[kind][key] for key in ("status", "category", "issuer") if key in EXAMPLES[kind]
    )
    page.filter.setCurrentText(selected)
    assert page.table.rowCount() == 1
    page.table.selectRow(0)
    qtbot.mouseClick(button(page, "View / Edit"), Qt.MouseButton.LeftButton)
    dialog = dialog_for(page)
    fill(dialog, {"notes": "Edited through real widgets"})
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(lambda: page.records[0].version == 2, timeout=15000)
    assert page.records[0].id == record_id
    with closing(connect(tmp_path / "mycmd.sqlite3")) as db:
        assert Service(db, owner_id()).get(record_id).data["notes"] == "Edited through real widgets"
    page.table.selectRow(0)

    def confirm():
        popup = QApplication.activeModalWidget()
        assert isinstance(popup, QMessageBox)
        popup.button(QMessageBox.StandardButton.Yes).click()

    QTimer.singleShot(50, confirm)
    qtbot.mouseClick(button(page, "Delete"), Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.records == [])
    with closing(connect(tmp_path / "mycmd.sqlite3")) as db:
        service = Service(db, owner_id())
        assert service.get(record_id, include_deleted=True).deleted_at
        assert [r["action"] for r in service.pending()] == ["create", "update", "delete"]


def test_validation_and_cli_interoperability_restart(qtbot, window, tmp_path):
    page = window.entities["projects"]
    window.navigation.setCurrentRow(2)
    dialog = RecordDialog("projects", window.controller, parent=page)
    qtbot.addWidget(dialog)
    dialog.open()
    qtbot.mouseClick(
        dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
    )
    assert dialog.error.text()
    assert dialog.isVisible()
    fill(dialog, EXAMPLES["projects"])
    fill(dialog, {"started_at": "2026-12-01", "finished_at": "2026-01-01"})
    dialog.save()
    assert "precedes" in dialog.error.text()
    fill(dialog, {"started_at": "", "finished_at": ""})
    save(qtbot, dialog)
    qtbot.waitUntil(lambda: len(page.records) == 1, timeout=15000)
    record_id = page.records[0].id
    env = os.environ.copy()
    env["MYCMD_DATA_DIR"] = str(tmp_path)
    shown = subprocess.run(
        [sys.executable, "-m", "mycmd", "projects", "show", record_id],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert shown.returncode == 0 and "GUI project" in shown.stdout
    edited = subprocess.run(
        [sys.executable, "-m", "mycmd", "projects", "edit", record_id, "title", "CLI update"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert edited.returncode == 0, edited.stderr
    page.refresh()
    qtbot.waitUntil(lambda: page.records[0].data["title"] == "CLI update")
    window.close()
    qtbot.waitUntil(lambda: window.closed)
    reopened = MainWindow(root=tmp_path)
    qtbot.addWidget(reopened)
    reopened.show()
    try:
        qtbot.waitUntil(lambda: reopened.ready)
        reopened.navigation.setCurrentRow(2)
        qtbot.waitUntil(lambda: len(reopened.entities["projects"].records) == 1)
        assert reopened.entities["projects"].records[0].data["title"] == "CLI update"
    finally:
        reopened.close()
        qtbot.waitUntil(lambda: reopened.closed)


def test_form_preserves_list_items_when_editing_notes(qtbot, window, tmp_path):
    with closing(connect(tmp_path / "mycmd.sqlite3")) as db:
        record = Service(db, owner_id()).create(
            "projects",
            EXAMPLES["projects"]
            | {
                "technologies": ["C, C++", "embedded\nnewline"],
                "links": ["https://example.com/a,b"],
            },
        )
    dialog = RecordDialog("projects", window.controller, record, window)
    qtbot.addWidget(dialog)
    assert dialog.values()["technologies"] == ["C, C++", "embedded\nnewline"]
    assert dialog.values()["links"] == ["https://example.com/a,b"]


def test_duplicate_and_stale_dialog_preserve_database(qtbot, window, tmp_path):
    with closing(connect(tmp_path / "mycmd.sqlite3")) as db:
        service = Service(db, owner_id())
        record = service.create("projects", EXAMPLES["projects"])
        updated = service.update(record.id, {"notes": "Concurrent writer"}, expected_version=1)
    stale = RecordDialog("projects", window.controller, record, window)
    qtbot.addWidget(stale)
    stale.open()
    fill(stale, {"notes": "Must not overwrite"})
    stale.save()
    qtbot.waitUntil(lambda: not stale.saving)
    assert stale.isVisible()
    assert "changed" in stale.error.text()
    # Restore displayed original fields so teardown does not need a discard prompt.
    fill(stale, {"notes": ""})
    stale.reject()
    duplicate = RecordDialog("projects", window.controller, parent=window)
    qtbot.addWidget(duplicate)
    duplicate.open()
    fill(duplicate, EXAMPLES["projects"])
    duplicate.save()
    qtbot.waitUntil(lambda: not duplicate.saving)
    assert duplicate.isVisible()
    assert "constraint" in duplicate.error.text().lower()
    duplicate.initial = duplicate.values()
    duplicate.reject()
    with closing(connect(tmp_path / "mycmd.sqlite3")) as db:
        service = Service(db, owner_id())
        assert service.get(record.id) == updated
        assert len(service.pending()) == 2
