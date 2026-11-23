"""Schema-driven native forms using the existing domain validator."""

import json

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from mycmd.core.models import ENUMS, FIELDS, REQUIRED, Record, validate
from mycmd.gui.controller import Controller


class RecordDialog(QDialog):
    def __init__(
        self,
        kind: str,
        controller: Controller,
        record: Record | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.kind, self.controller, self.record = kind, controller, record
        self.setWindowTitle(f"{'Edit' if record else 'Create'} {kind.rstrip('s')}")
        self.resize(560, 560)
        self.fields: dict[str, QLineEdit | QPlainTextEdit | QComboBox] = {}
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        for key in sorted(FIELDS[kind], key=lambda k: (k not in REQUIRED[kind], k)):
            field: QLineEdit | QPlainTextEdit | QComboBox
            if (kind, key) in ENUMS:
                field = QComboBox()
                field.addItems(sorted(ENUMS[kind, key]))
            elif key in {"description", "notes", "links", "technologies"}:
                field = QPlainTextEdit()
                field.setMaximumHeight(100)
                if key in {"links", "technologies"}:
                    field.setPlaceholderText('JSON list, for example ["Python", "SQLite"]')
            else:
                field = QLineEdit()
                if key.endswith("_at"):
                    field.setPlaceholderText("YYYY-MM-DD (optional)")
            field.setObjectName(key)
            field.setAccessibleName(key.replace("_", " "))
            value = record.data.get(key) if record else None
            text = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, list)
                else str(value or "")
            )
            if isinstance(field, QComboBox):
                if text:
                    field.setCurrentText(text)
            elif isinstance(field, QPlainTextEdit):
                field.setPlainText(text)
            else:
                field.setText(text)
            self.fields[key] = field
            form.addRow(
                key.replace("_", " ").title() + (" *" if key in REQUIRED[kind] else ""), field
            )
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setAccessibleName("Form error")
        outer.addWidget(self.error)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self.initial = self.values()
        self.saving = False

    def values(self) -> dict[str, object]:
        data: dict[str, object] = {}
        for key, field in self.fields.items():
            text = (
                field.currentText()
                if isinstance(field, QComboBox)
                else field.toPlainText()
                if isinstance(field, QPlainTextEdit)
                else field.text()
            )
            if key in {"links", "technologies"}:
                try:
                    data[key] = json.loads(text) if text.strip() else []
                except ValueError:
                    data[key] = text
            else:
                data[key] = text if text or key in REQUIRED[self.kind] else None
        return data

    def save(self) -> None:
        try:
            data = validate(self.kind, self.values())
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        self.saving = True
        self.buttons.setEnabled(False)
        self.error.setText("Saving…")
        record = self.record
        self.controller.submit(
            lambda service: (
                service.update(record.id, data, expected_version=record.version)
                if record
                else service.create(self.kind, data)
            ),
            self.saved,
            self.failed,
        )

    def saved(self, result: object) -> None:
        self.saving = False
        self.controller.changed.emit()
        self.accept()

    def failed(self, message: str) -> None:
        if self.saving:
            self.saving = False
            self.buttons.setEnabled(True)
            self.error.setText(message)

    def reject(self) -> None:
        if self.saving:
            return
        if (
            self.values() != self.initial
            and QMessageBox.question(
                self,
                "Discard changes?",
                "Discard unsaved changes?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            != QMessageBox.StandardButton.Discard
        ):
            return
        super().reject()
