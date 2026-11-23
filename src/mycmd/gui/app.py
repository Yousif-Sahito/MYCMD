"""Optional desktop entry point."""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from mycmd.gui.main_window import MainWindow


def run() -> int:
    application = QApplication(sys.argv[:1])
    application.setApplicationName("MYCMD")
    application.setOrganizationName("MYCMD")
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, "MYCMD startup error", str(exc))
        return 1
    window.show()
    return application.exec()
