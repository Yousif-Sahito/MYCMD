"""Actual xterm/WebChannel/PTY end-to-end checks, without mocked shell output."""

import json
import os
import shlex
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from mycmd.gui.main_window import MainWindow
from mycmd.terminal.models import SessionState


def js(qtbot, page, source):
    result = []
    page.runJavaScript(source, result.append)
    qtbot.waitUntil(lambda: bool(result), timeout=10000)
    return result[0]


def buffer(qtbot, page):
    return js(
        qtbot,
        page,
        "Array.from({length:terminal.buffer.active.length},(_,i)=>terminal.buffer.active.getLine(i).translateToString(true)).join('\\n')",
    )


def wait_text(qtbot, page, text):
    qtbot.waitUntil(lambda: text in buffer(qtbot, page), timeout=20000)


@pytest.mark.parametrize("shell", ["cmd", "powershell"] if os.name == "nt" else ["bash"])
def test_real_gui_shell_keyboard_render_resize_clipboard_restart(qtbot, tmp_path, shell):
    window = MainWindow(root=tmp_path)
    window.show()
    terminal = window.terminal
    try:
        window.navigation.setCurrentRow(1)
        qtbot.waitUntil(lambda: terminal.renderer_ready, timeout=20000)
        terminal.preferences.cwd = str(tmp_path)
        terminal.shell.setCurrentText(shell)
        terminal.start()
        qtbot.waitUntil(
            lambda: terminal.session is not None and terminal.session.state is SessionState.RUNNING,
            timeout=15000,
        )
        session = terminal.session
        if shell == "bash":
            qtbot.waitUntil(lambda: "$ " in buffer(qtbot, terminal.page), timeout=10000)
        else:
            qtbot.waitUntil(lambda: ">" in buffer(qtbot, terminal.page), timeout=10000)
        # Native keyboard events enter xterm, cross WebChannel, then reach the real shell.
        terminal.web.setFocus()
        js(qtbot, terminal.page, "terminal.focus()")
        qtbot.keyClicks(terminal.web.focusProxy(), "echo GUI_KEYBOARD_42")
        qtbot.keyClick(terminal.web.focusProxy(), Qt.Key.Key_Return)
        wait_text(qtbot, terminal.page, "GUI_KEYBOARD_42")
        python = (
            f'& "{sys.executable}"'
            if shell == "powershell"
            else f'"{sys.executable}"'
            if shell == "cmd"
            else shlex.quote(sys.executable)
        )
        code = "import sys;print(chr(27)+'[31m'+chr(9731)+'_REAL_COLOR'+chr(27)+'[0m',flush=True)"
        terminal.write(f'{python} -c "{code}"\r')
        wait_text(qtbot, terminal.page, "☃_REAL_COLOR")
        assert "[31m" not in buffer(qtbot, terminal.page).split("☃_REAL_COLOR")[-1]
        old = terminal.dimensions
        window.resize(1350, 850)
        qtbot.waitUntil(lambda: terminal.dimensions != old, timeout=10000)
        qtbot.waitUntil(lambda: (session.columns, session.rows) == terminal.dimensions)
        QApplication.clipboard().setText("echo GUI_PASTED_84")
        terminal.paste()
        wait_text(qtbot, terminal.page, "echo GUI_PASTED_84")
        terminal.write("\r")
        qtbot.waitUntil(lambda: buffer(qtbot, terminal.page).count("GUI_PASTED_84") >= 2)
        js(qtbot, terminal.page, "terminal.selectAll()")
        terminal.copy()
        qtbot.waitUntil(lambda: "GUI_PASTED_84" in QApplication.clipboard().text())
        terminal.search.setText("GUI_KEYBOARD_42")
        qtbot.keyClick(terminal.search, Qt.Key.Key_Return)
        qtbot.waitUntil(
            lambda: js(qtbot, terminal.page, "terminal.getSelection()") == "GUI_KEYBOARD_42"
        )
        # Persistent environment, working directory, pipes and redirection stay in one shell.
        if shell == "cmd":
            command = "set MYCMD_GUI_VALUE=kept\r"
            check = "echo %MYCMD_GUI_VALUE%> gui-output.txt & type gui-output.txt | findstr kept\r"
        elif shell == "powershell":
            command = "$env:MYCMD_GUI_VALUE='kept'\r"
            check = "$env:MYCMD_GUI_VALUE | Out-File gui-output.txt; Get-Content gui-output.txt\r"
        else:
            command = "export MYCMD_GUI_VALUE=kept\r"
            check = 'printf "%s\\n" "$MYCMD_GUI_VALUE" > gui-output.txt; cat gui-output.txt | cat\r'
        terminal.write(command)
        terminal.write(check)
        qtbot.waitUntil(lambda: (tmp_path / "gui-output.txt").exists(), timeout=10000)
        qtbot.waitUntil(
            lambda: (
                (tmp_path / "gui-output.txt").stat().st_size >= (12 if shell == "powershell" else 5)
            ),
            timeout=10000,
        )
        assert "kept" in (tmp_path / "gui-output.txt").read_text(
            encoding="utf-16" if shell == "powershell" else "utf-8"
        )
        terminal.write(
            f"{python} -c \"import time;print('STREAM_'+'STARTED',flush=True);time.sleep(30)\"\r"
        )
        wait_text(qtbot, terminal.page, "STREAM_STARTED")
        terminal.interrupt()
        wait_text(qtbot, terminal.page, "KeyboardInterrupt")
        if shell == "powershell":
            qtbot.waitUntil(
                lambda: buffer(qtbot, terminal.page).rstrip().endswith(">"), timeout=10000
            )
        terminal.write("echo INTERRUPT_RETURNED\r")
        wait_text(qtbot, terminal.page, "INTERRUPT_RETURNED")
        artifacts = Path(".tools/phase4-visual")
        artifacts.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(artifacts / f"terminal-{shell}.png"))
        terminal.close_session()
        qtbot.waitUntil(lambda: terminal.session is None, timeout=20000)
        assert session.state is SessionState.CLOSED
        assert terminal.reader is not None and not terminal.reader.is_alive()
        terminal.start()
        qtbot.waitUntil(
            lambda: terminal.session is not None and terminal.session.state is SessionState.RUNNING,
            timeout=15000,
        )
        terminal.write("echo SECOND_SESSION\r")
        wait_text(qtbot, terminal.page, "SECOND_SESSION")
    finally:
        window.close()
        qtbot.waitUntil(lambda: window.closed, timeout=20000)


def test_terminal_output_is_text_not_html(qtbot, tmp_path):
    window = MainWindow(root=tmp_path)
    window.show()
    try:
        window.navigation.setCurrentRow(1)
        qtbot.waitUntil(lambda: window.terminal.renderer_ready, timeout=20000)
        payload = "<img src=x onerror=alert(1)>"
        js(qtbot, window.terminal.page, f"terminal.write({json.dumps(payload)})")
        wait_text(qtbot, window.terminal.page, payload)
        assert js(qtbot, window.terminal.page, "document.querySelectorAll('img').length") == 0
    finally:
        window.close()
        qtbot.waitUntil(lambda: window.closed, timeout=20000)
