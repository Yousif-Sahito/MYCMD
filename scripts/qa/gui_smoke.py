"""External installed-wheel GUI harness: real Qt window, readiness and shutdown."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import mycmd
from mycmd.gui.main_window import MainWindow


def main() -> int:
    installed = Path(mycmd.__file__).resolve()
    if not installed.is_relative_to(Path(sys.prefix).resolve()):
        raise RuntimeError(f"GUI smoke did not import installed package: {installed}")
    application = QApplication([])
    window = MainWindow(root=Path(os.environ["MYCMD_DATA_DIR"]))
    window.show()
    outcome = {"ready": False}
    poll = QTimer()

    def inspect() -> None:
        if window.ready and window.terminal.renderer_ready and window.isVisible():
            outcome["ready"] = True
            poll.stop()
            window.close()

    poll.timeout.connect(inspect)
    poll.start(50)
    QTimer.singleShot(30000, application.quit)
    result = application.exec()
    if not outcome["ready"]:
        window.close()
        raise RuntimeError("Installed GUI failed to reach visible, loaded state within 30 seconds")
    if result != 0:
        raise RuntimeError(f"Qt event loop failed with exit {result}")
    if not window.closed:
        raise RuntimeError("Installed GUI did not complete asynchronous shutdown")
    print("Installed GUI main window loaded and closed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
