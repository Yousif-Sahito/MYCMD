"""Five native data pages backed by shared services."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mycmd.core.models import ENUMS, Record
from mycmd.gui.controller import Controller
from mycmd.gui.forms import RecordDialog


class EntityPage(QWidget):
    def __init__(self, kind: str, controller: Controller):
        super().__init__()
        self.kind, self.controller = kind, controller
        self.records: list[Record] = []
        self.visible_records: list[Record] = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(kind.title()))
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"Search {kind}")
        self.search.setAccessibleName(f"Search {kind}")
        self.search.textChanged.connect(self.render_records)
        bar.addWidget(self.search)
        self.filter = QComboBox()
        self.filter.setAccessibleName("Filter records")
        self.filter.addItem("All")
        self.filter.currentTextChanged.connect(self.render_records)
        bar.addWidget(self.filter)
        for title, action in [
            ("Create", self.create_record),
            ("View / Edit", self.edit),
            ("Delete", self.delete),
            ("Refresh", self.refresh),
        ]:
            button = QPushButton(title)
            button.clicked.connect(action)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Status / Category", "Updated"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 240)
        self.table.setColumnWidth(1, 180)
        self.table.setAccessibleName(f"{kind} records")
        self.table.cellDoubleClicked.connect(self.edit)
        layout.addWidget(self.table)
        self.empty = QLabel("No records yet. Choose Create to add one.")
        layout.addWidget(self.empty)
        controller.changed.connect(self.refresh)

    def refresh(self) -> None:
        self.empty.setText("Loading…")
        self.controller.submit(lambda s: s.list(self.kind), self.loaded)

    def loaded(self, value: object) -> None:
        assert isinstance(value, list)
        self.records = value
        selected = self.filter.currentText()
        options = sorted(
            {
                str(r.data.get("status") or r.data.get("category") or r.data.get("issuer") or "")
                for r in self.records
            }
            | ENUMS.get((self.kind, "status"), set())
        )
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItems(["All"] + [v for v in options if v])
        self.filter.setCurrentText(selected if selected in options else "All")
        self.filter.blockSignals(False)
        self.render_records()

    def render_records(self) -> None:
        query, category = self.search.text().casefold(), self.filter.currentText()
        self.visible_records = [
            r
            for r in self.records
            if query in " ".join(str(v) for v in r.data.values()).casefold()
            and (
                category == "All"
                or category in {r.data.get("status"), r.data.get("category"), r.data.get("issuer")}
            )
        ]
        self.table.setRowCount(len(self.visible_records))
        for row, record in enumerate(self.visible_records):
            values = [
                record.data.get("title")
                or record.data.get("name")
                or record.data.get("institution"),
                record.data.get("status")
                or record.data.get("category")
                or record.data.get("issuer"),
                record.updated_at,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setToolTip(str(value or ""))
                self.table.setItem(row, column, item)
        self.empty.setText(
            "No matching records." if self.records else "No records yet. Choose Create to add one."
        )
        self.empty.setVisible(not self.visible_records)

    def create_record(self) -> None:
        dialog = RecordDialog(self.kind, self.controller, parent=self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()

    def edit(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            dialog = RecordDialog(self.kind, self.controller, self.visible_records[row], self)
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.open()

    def delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        record = self.visible_records[row]
        if (
            QMessageBox.question(
                self,
                "Delete record?",
                "Delete this record? A local tombstone is retained for future sync.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.controller.submit(
                lambda s: s.delete(record.id, expected_version=record.version),
                lambda _: self.controller.changed.emit(),
            )
