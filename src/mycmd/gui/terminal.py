"""Trusted local xterm renderer and bounded asynchronous Phase 3 transport."""

import asyncio
import base64
import json
import queue
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mycmd.gui.settings import Preferences
from mycmd.terminal.discovery import discover_shell
from mycmd.terminal.models import OutputEvent, SessionState
from mycmd.terminal.session import TerminalSession

RESOURCES = Path(__file__).parent / "resources"


class LocalRequests(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        url = info.requestUrl()
        allowed = url.toString() == "qrc:///qtwebchannel/qwebchannel.js"
        if url.isLocalFile():
            allowed = Path(url.toLocalFile()).resolve().parent == RESOURCES.resolve()
        info.block(not allowed)


class LocalPage(QWebEnginePage):
    def acceptNavigationRequest(
        self, url: QUrl | str, kind: QWebEnginePage.NavigationType, main: bool
    ) -> bool:
        return main and url == QUrl.fromLocalFile(str(RESOURCES / "terminal.html"))


class Bridge(QObject):
    output = Signal(str)
    control = Signal(str)
    initialized = Signal()
    written = Signal(str)
    resized = Signal(int, int)
    copied = Signal(str)
    paste = Signal()

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.waiting = False

    @Slot()
    def ready(self) -> None:
        self.initialized.emit()

    @Slot()
    def acknowledge(self) -> None:
        self.waiting = False

    @Slot(str)
    def input(self, data: str) -> None:
        if len(data) <= 1048576:
            self.written.emit(data)

    @Slot(int, int)
    def resize(self, columns: int, rows: int) -> None:
        if 2 <= columns <= 1000 and 1 <= rows <= 500:
            self.resized.emit(columns, rows)

    @Slot(str)
    def selection(self, text: str) -> None:
        self.copied.emit(text)

    @Slot()
    def pasteRequest(self) -> None:
        self.paste.emit()


class TerminalPage(QWidget):
    def __init__(self, preferences: Preferences):
        super().__init__()
        self.preferences = preferences
        self.session: TerminalSession | None = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mycmd-terminal")
        self.jobs: list[Future[None]] = []
        self.close_job: Future[None] | None = None
        self.events: queue.Queue[OutputEvent] = queue.Queue(64)
        self.stop = threading.Event()
        self.reader: threading.Thread | None = None
        self.renderer_ready = False
        self.dimensions = (80, 24)
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.shell = QComboBox()
        self.shell.setAccessibleName("Shell selection")
        self.shell.addItems(
            ["cmd", "powershell", "pwsh"] if sys.platform == "win32" else ["bash", "zsh", "sh"]
        )
        if preferences.shell:
            self.shell.setCurrentText(preferences.shell)
        bar.addWidget(self.shell)
        for text, callback in [
            ("New session", self.start),
            ("Close session", self.close_session),
            ("Copy", self.copy),
            ("Paste", self.paste),
            ("Clear", self.clear),
            ("Interrupt", self.interrupt),
        ]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.status = QLabel("No session. Shells run locally as the current user.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search scrollback; press Enter")
        self.search.setAccessibleName("Search terminal scrollback")
        self.search.returnPressed.connect(lambda: self.command("search", text=self.search.text()))
        layout.addWidget(self.search)
        self.web = QWebEngineView()
        self.web.setAccessibleName("Local terminal")
        self.profile = QWebEngineProfile(self.web)
        self.page = LocalPage(self.profile, self.web)
        self.interceptor = LocalRequests(self.page)
        self.page.profile().setUrlRequestInterceptor(self.interceptor)
        self.web.setPage(self.page)
        for attribute in [
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
        ]:
            self.page.settings().setAttribute(attribute, False)
        self.channel = QWebChannel(self.page)
        self.bridge = Bridge(self.channel)
        self.channel.registerObject("bridge", self.bridge)
        self.page.setWebChannel(self.channel)
        self.bridge.initialized.connect(self.ready)
        self.bridge.written.connect(self.write)
        self.bridge.resized.connect(self.resize_terminal)
        self.bridge.copied.connect(lambda text: QApplication.clipboard().setText(text))
        self.bridge.paste.connect(self.paste)
        self.web.load(QUrl.fromLocalFile(str(RESOURCES / "terminal.html")))
        self.web.loadFinished.connect(self.load_finished)
        self.page.renderProcessTerminated.connect(self.renderer_failed)
        layout.addWidget(self.web)
        # Qt deletes children in creation order. Reparent the profile after the
        # web view so its page is destroyed before the profile it depends on.
        self.profile.setParent(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(15)

    def load_finished(self, success: bool) -> None:
        if not success:
            self.renderer_ready = False
            self.status.setText(
                "Terminal renderer could not load. Close and reopen the application."
            )

    def renderer_failed(self) -> None:
        self.renderer_ready = False
        self.status.setText("Terminal renderer stopped. Closing the local shell.")
        self.close_session()

    def ready(self) -> None:
        self.renderer_ready = True
        self.apply_preferences()

    def command(self, action: str, **values: object) -> None:
        self.bridge.control.emit(json.dumps({"action": action, **values}))

    def apply_preferences(self) -> None:
        self.command(
            "settings",
            theme=self.preferences.theme,
            font_size=self.preferences.font_size,
            scrollback=self.preferences.scrollback,
        )

    def start(self) -> None:
        if not self.renderer_ready or self.jobs:
            self.status.setText("Terminal is loading or completing an operation.")
            return
        if self.session is not None:
            self.status.setText("Close the current session before starting another.")
            return
        try:
            session = TerminalSession(
                discover_shell(self.shell.currentText()),
                self.preferences.cwd,
                columns=self.dimensions[0],
                rows=self.dimensions[1],
            )
        except Exception as exc:
            self.status.setText(str(exc))
            return
        self.session = session
        self.stop.clear()
        self.status.setText(f"Starting {session.shell.name} in {session.cwd}…")
        self.jobs.append(self.executor.submit(session.start))
        self.reader = threading.Thread(target=self.consume, args=(session,), daemon=True)
        self.reader.start()

    def consume(self, session: TerminalSession) -> None:
        async def read() -> None:
            async for event in session.read_events():
                while not self.stop.is_set():
                    try:
                        self.events.put(event, timeout=0.1)
                        break
                    except queue.Full:
                        continue
                if self.stop.is_set():
                    return

        asyncio.run(read())

    def poll(self) -> None:
        if self.close_job is not None and self.close_job.done():
            try:
                self.close_job.result()
            except Exception as exc:
                self.status.setText(f"Close failed; retry closing: {exc}")
            else:
                self.session = None
                self.status.setText("Session closed")
                while not self.events.empty():
                    self.events.get_nowait()
            self.close_job = None
        for job in list(self.jobs):
            if job.done():
                self.jobs.remove(job)
                try:
                    job.result()
                except Exception as exc:
                    self.status.setText(str(exc))
        if not self.renderer_ready or self.bridge.waiting:
            return
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            return
        if event.data:
            self.bridge.waiting = True
            self.bridge.output.emit(base64.b64encode(event.data).decode("ascii"))
        if event.state:
            self.status.setText(
                f"{self.shell.currentText()}: {event.state.value}; exit: {event.exit_code}"
            )
        if event.error:
            self.status.setText(event.error)

    def write(self, text: str) -> None:
        session = self.session
        if session and session.state is SessionState.RUNNING:
            self.jobs.append(self.executor.submit(session.write, text.encode("utf-8")))

    def resize_terminal(self, columns: int, rows: int) -> None:
        self.dimensions = columns, rows
        session = self.session
        if session and session.state is SessionState.RUNNING:
            self.jobs.append(self.executor.submit(session.resize, columns, rows))

    def interrupt(self) -> None:
        session = self.session
        if session and session.state is SessionState.RUNNING:
            self.jobs.append(self.executor.submit(session.interrupt))

    def copy(self) -> None:
        self.command("copy")

    def paste(self) -> None:
        self.command("paste", text=QApplication.clipboard().text())

    def clear(self) -> None:
        self.command("clear")

    def close_session(self) -> None:
        session = self.session
        if session and self.close_job is None:
            self.stop.set()
            self.close_job = self.executor.submit(self.stop_session, session)
            self.status.setText("Closing session…")

    def stop_session(self, session: TerminalSession) -> None:
        session.terminate()
        if self.reader:
            self.reader.join(5)
            if self.reader.is_alive():
                raise RuntimeError("Terminal reader did not stop")

    def shutdown(self) -> None:
        self.stop.set()
        if self.session:
            self.executor.submit(self.stop_session, self.session).result()
        self.executor.shutdown(wait=True, cancel_futures=False)
        if self.reader:
            self.reader.join(5)
