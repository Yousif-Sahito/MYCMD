"""Exercise the real WebEngine security boundary with bundled content."""

import base64
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtTest import QSignalSpy
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from pytestqt.qtbot import QtBot

from mycmd.gui.main_window import MainWindow
from mycmd.gui.settings import Preferences
from mycmd.gui.terminal import RESOURCES, Bridge, TerminalPage
from mycmd.terminal import TerminalSession, discover_shell


@pytest.fixture
def terminal_view(qtbot: QtBot, tmp_path: Path) -> Iterator[TerminalPage]:
    view = TerminalPage(Preferences(cwd=str(tmp_path)))
    qtbot.addWidget(view)
    view.resize(800, 500)
    view.show()
    qtbot.waitUntil(lambda: view.renderer_ready, timeout=15000)
    yield view
    view.timer.stop()
    view.shutdown()
    view.release_webengine()


def javascript(qtbot: QtBot, view: TerminalPage, source: str) -> object:
    results: list[object] = []
    view.page.runJavaScript(source, results.append)
    qtbot.waitUntil(lambda: bool(results), timeout=5000)
    return results[0]


def test_navigation_rejects_untrusted_origins(
    qtbot: QtBot, terminal_view: TerminalPage, tmp_path: Path
) -> None:
    trusted = QUrl.fromLocalFile(str(RESOURCES / "terminal.html"))
    malicious = tmp_path / "untrusted.html"
    malicious.write_text("<script>document.title='UNTRUSTED'</script>", encoding="utf-8")
    navigation = QWebEnginePage.NavigationType.NavigationTypeOther
    for destination in [
        QUrl("https://example.invalid/"),
        QUrl("data:text/html,<script>document.title='UNTRUSTED'</script>"),
        QUrl.fromLocalFile(str(malicious)),
    ]:
        assert not terminal_view.page.acceptNavigationRequest(destination, navigation, True)
        terminal_view.web.load(destination)
        qtbot.wait(100)
        assert terminal_view.web.url() != destination
        terminal_view.web.load(trusted)
        qtbot.waitUntil(lambda: terminal_view.web.url() == trusted, timeout=5000)
    assert not terminal_view.page.acceptNavigationRequest(trusted, navigation, False)


def test_csp_blocks_injected_script_and_network(qtbot: QtBot, terminal_view: TerminalPage) -> None:
    # runJavaScript is a trusted test harness; the inserted DOM script must still
    # obey the document's CSP rather than acquire access to WebChannel.
    javascript(
        qtbot,
        terminal_view,
        "window.injectedExecuted=false; const s=document.createElement('script');"
        "s.textContent='window.injectedExecuted=true';document.body.appendChild(s);"
        "window.fetchState='pending';fetch('https://example.invalid/')"
        ".then(()=>window.fetchState='allowed').catch(()=>window.fetchState='blocked');true",
    )
    qtbot.waitUntil(
        lambda: javascript(qtbot, terminal_view, "window.fetchState") != "pending", timeout=5000
    )
    assert javascript(qtbot, terminal_view, "window.injectedExecuted") is False
    assert javascript(qtbot, terminal_view, "window.fetchState") == "blocked"
    assert javascript(qtbot, terminal_view, "window.open('https://example.invalid/')===null")


def test_local_subresource_outside_bundle_is_blocked(
    qtbot: QtBot, terminal_view: TerminalPage, tmp_path: Path
) -> None:
    script = tmp_path / "outside-bundle.js"
    script.write_text("window.outsideBundleExecuted=true", encoding="utf-8")
    url = json.dumps(QUrl.fromLocalFile(str(script)).toString())
    javascript(
        qtbot,
        terminal_view,
        "window.outsideBundleState='pending';const outside=document.createElement('script');"
        f"outside.src={url};outside.onload=()=>window.outsideBundleState='allowed';"
        "outside.onerror=()=>window.outsideBundleState='blocked';"
        "document.body.appendChild(outside);true",
    )
    qtbot.waitUntil(
        lambda: javascript(qtbot, terminal_view, "window.outsideBundleState") != "pending",
        timeout=5000,
    )
    assert javascript(qtbot, terminal_view, "window.outsideBundleState") == "blocked"
    assert javascript(qtbot, terminal_view, "typeof window.outsideBundleExecuted") == "undefined"


def test_webengine_dangerous_permissions_disabled(terminal_view: TerminalPage) -> None:
    assert terminal_view.page.profile() is not QWebEngineProfile.defaultProfile()
    assert terminal_view.page.profile().isOffTheRecord()
    for attribute in [
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
        QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
        QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
    ]:
        assert not terminal_view.page.settings().testAttribute(attribute)


def test_bridge_rejects_oversized_input_and_invalid_dimensions(qapp: object) -> None:
    parent = QObject()
    bridge = Bridge(parent)
    written = QSignalSpy(bridge.written)
    resized = QSignalSpy(bridge.resized)
    bridge.input("x" * (1048576 + 1))
    assert written.count() == 0
    bridge.input("echo local\r")
    assert written.count() == 1
    for columns, rows in [(0, 24), (80, 0), (1001, 24), (80, 501)]:
        bridge.resize(columns, rows)
    assert resized.count() == 0
    bridge.resize(80, 24)
    assert resized.count() == 1


def test_shell_output_is_terminal_data_not_html(qtbot: QtBot, terminal_view: TerminalPage) -> None:
    payload = b"<script>window.shellInjected=true</script>\r\n"
    terminal_view.bridge.waiting = True
    terminal_view.bridge.output.emit(base64.b64encode(payload).decode("ascii"))
    qtbot.waitUntil(lambda: not terminal_view.bridge.waiting, timeout=5000)
    assert javascript(qtbot, terminal_view, "typeof window.shellInjected") == "undefined"
    assert "<script>" in str(
        javascript(qtbot, terminal_view, "terminal.buffer.active.getLine(0).translateToString()")
    )


def test_failed_session_close_retains_retry_handle(
    qtbot: QtBot, terminal_view: TerminalPage, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Failure injection tests the adapter's lifecycle contract; no real child
    # is started here, and this is not counted as real-shell cleanup evidence.
    session = TerminalSession(discover_shell(), tmp_path)
    terminal_view.session = session

    def fail_termination(timeout: float = 3.0) -> None:
        raise RuntimeError("injected native cleanup failure")

    with monkeypatch.context() as patch:
        patch.setattr(session, "terminate", fail_termination)
        terminal_view.close_session()
        qtbot.waitUntil(lambda: terminal_view.close_job is None, timeout=5000)
        assert terminal_view.session is session
        assert "Close failed" in terminal_view.status.text()
        assert terminal_view.session is session
    terminal_view.close_session()
    qtbot.waitUntil(lambda: terminal_view.session is None, timeout=5000)


def test_window_shutdown_failure_restores_polling_and_allows_retry(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    window = MainWindow(tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.ready and window.terminal.renderer_ready, timeout=15000)
    errors: list[str] = []

    def fail_shutdown() -> None:
        raise RuntimeError("injected shutdown failure")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(window.terminal, "shutdown", fail_shutdown)
            patch.setattr(window, "show_error", errors.append)
            window.close()
            qtbot.waitUntil(lambda: bool(errors), timeout=5000)
            assert not window.closed
            assert not window.closing
            assert window.isEnabled()
            assert window.controller.timer.isActive()
            assert window.terminal.timer.isActive()
            assert "injected shutdown failure" in errors[0]
    finally:
        window.close()
        qtbot.waitUntil(lambda: window.closed, timeout=10000)
