"""Desktop navigation, live summaries and application lifecycle."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mycmd.config import data_directory
from mycmd.core.models import FIELDS
from mycmd.gui.controller import Controller
from mycmd.gui.entities import EntityPage
from mycmd.gui.settings import Preferences
from mycmd.gui.terminal import TerminalPage


class MainWindow(QMainWindow):
    def __init__(self, root: Path | None = None):
        super().__init__()
        self.root = root or data_directory()
        self.ready = False
        self.closing = False
        self.closed = False
        self.shutdown_executor = ThreadPoolExecutor(max_workers=1)
        self.shutdown_job: Future[None] | None = None
        self.preferences = Preferences.load(self.root)
        self.controller = Controller(self.root)
        self.setWindowTitle("MYCMD · Personal Command Centre")
        self.resize(1100, 720)
        self.setMinimumSize(720, 480)
        central = QWidget()
        layout = QHBoxLayout(central)
        self.navigation = QListWidget()
        self.navigation.setAccessibleName("Main navigation")
        self.navigation.setMaximumWidth(180)
        self.navigation.addItems(
            ["Dashboard", "Terminal", *[k.title() for k in FIELDS], "Sync", "Settings"]
        )
        layout.addWidget(self.navigation)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.dashboard = QLabel("Loading local data…")
        self.dashboard.setWordWrap(True)
        self.dashboard.setMargin(24)
        self.stack.addWidget(self.dashboard)
        self.terminal = TerminalPage(self.preferences)
        self.stack.addWidget(self.terminal)
        self.entities: dict[str, EntityPage] = {}
        for kind in FIELDS:
            page = EntityPage(kind, self.controller)
            self.entities[kind] = page
            self.stack.addWidget(page)
        self.sync = QLabel("Loading local queue…")
        self.sync.setWordWrap(True)
        self.sync.setMargin(24)
        self.stack.addWidget(self.sync)
        self.stack.addWidget(self.settings_page())
        self.navigation.currentRowChanged.connect(self.navigate)
        self.navigation.setCurrentRow(0)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(120)
        self.progress.setAccessibleName("Loading local data")
        self.statusBar().addPermanentWidget(self.progress)
        self.controller.busy.connect(self.progress.setVisible)
        self.controller.error.connect(self.show_error)
        self.controller.changed.connect(self.refresh)
        self.refresh()
        self.apply_theme()
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.finish_close)

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if isinstance(page, EntityPage):
            page.refresh()
        elif index in {0, 7}:
            self.refresh()

    def refresh(self) -> None:
        self.controller.submit(
            lambda s: ({kind: len(s.list(kind)) for kind in FIELDS}, len(s.pending())), self.summary
        )

    def summary(self, result: object) -> None:
        assert isinstance(result, tuple)
        counts, pending = result
        self.dashboard.setText(
            "MYCMD\nYour local workspace\n\n"
            + "\n".join(f"{kind.title()}: {count}" for kind, count in counts.items())
            + f"\n\nPending operations: {pending}\nLocal database: available"
            "\nOnline synchronization: unavailable (Phase 7)"
        )
        self.sync.setText(
            f"Local synchronization status\n\nPending operations: {pending}"
            "\n\nChanges are safely queued locally."
            " Online synchronization is not implemented until Phase 7."
            " No last-sync timestamp is available."
        )
        self.ready = True
        self.controller.loaded.emit()
        self.statusBar().showMessage("Local data refreshed", 3000)

    def show_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.critical(self, "MYCMD error", message)

    def settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Desktop preferences"))
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        self.theme.setCurrentText(self.preferences.theme)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 40)
        self.font_size.setValue(self.preferences.font_size)
        self.scrollback = QSpinBox()
        self.scrollback.setRange(100, 100000)
        self.scrollback.setValue(self.preferences.scrollback)
        self.preferred_shell = QComboBox()
        self.preferred_shell.addItem("")
        self.preferred_shell.addItems(
            [self.terminal.shell.itemText(i) for i in range(self.terminal.shell.count())]
        )
        self.preferred_shell.setCurrentText(self.preferences.shell)
        self.cwd = QLineEdit(self.preferences.cwd)
        for title, widget in [
            ("Theme", self.theme),
            ("Terminal font size", self.font_size),
            ("Scrollback lines", self.scrollback),
            ("Preferred shell", self.preferred_shell),
            ("Default working directory", self.cwd),
        ]:
            widget.setAccessibleName(title)
            form.addRow(title, widget)
        layout.addLayout(form)
        save = QPushButton("Save preferences")
        save.clicked.connect(self.save_preferences)
        layout.addWidget(save)
        layout.addStretch()
        return page

    def save_preferences(self) -> None:
        preferences = Preferences(
            self.theme.currentText(),
            self.font_size.value(),
            self.scrollback.value(),
            self.preferred_shell.currentText(),
            self.cwd.text(),
        )
        try:
            preferences.save(self.root)
        except (ValueError, OSError) as exc:
            self.show_error(str(exc))
            return
        self.preferences = preferences
        self.terminal.preferences = preferences
        self.terminal.apply_preferences()
        self.apply_theme()
        self.statusBar().showMessage("Preferences saved", 4000)

    def apply_theme(self) -> None:
        dark = self.preferences.theme == "dark"
        background, foreground, surface, border = (
            ("#111827", "#f3f4f6", "#1f2937", "#94a3b8")
            if dark
            else ("#f3f6fa", "#172033", "#ffffff", "#64748b")
        )
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(
                f"QWidget {{background:{background};color:{foreground};font-size:14px;}}"
                " QLineEdit,QPlainTextEdit,QComboBox,QSpinBox,QTableWidget,QListWidget "
                f"{{background:{surface};padding:6px;border:1px solid {border};}}"
                f" QPushButton {{padding:7px 10px;border:1px solid {border};border-radius:4px;}}"
                " QPushButton:focus,QLineEdit:focus,QComboBox:focus,QSpinBox:focus "
                "{border:2px solid #3b82f6;}"
                " QListWidget::item:selected,QTableWidget::item:selected "
                "{background:#1d4ed8;color:white;}"
                f" QLabel {{border:none;}}"
                f" QHeaderView::section {{background:{surface};color:{foreground};"
                f"padding:6px;border:1px solid {border};}}"
            )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.closed:
            event.accept()
            return
        event.ignore()
        if self.closing:
            return
        self.closing = True
        self.setEnabled(False)
        self.statusBar().showMessage("Closing sessions and finishing database work…")
        self.controller.timer.stop()
        self.terminal.timer.stop()
        self.shutdown_job = self.shutdown_executor.submit(self.cleanup)
        self.close_timer.start(30)

    def cleanup(self) -> None:
        self.terminal.shutdown()
        self.controller.executor.shutdown(wait=True, cancel_futures=True)

    def finish_close(self) -> None:
        if self.shutdown_job is not None and self.shutdown_job.done():
            self.close_timer.stop()
            try:
                self.shutdown_job.result()
            except Exception as exc:
                self.setEnabled(True)
                self.closing = False
                self.controller.timer.start(30)
                self.terminal.timer.start(15)
                self.show_error(f"Shutdown failed: {exc}")
                return
            self.closed = True
            self.shutdown_executor.shutdown(wait=False)
            self.close()
