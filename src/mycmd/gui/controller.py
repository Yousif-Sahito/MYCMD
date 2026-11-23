"""Serialized service jobs; each connection is confined to its worker thread."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from mycmd.config import owner_id
from mycmd.core.service import Service
from mycmd.storage.database import connect


class Controller(QObject):
    changed = Signal()
    error = Signal(str)
    busy = Signal(bool)
    loaded = Signal()

    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.owner = owner_id()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mycmd-data")
        self.pending: list[
            tuple[Future[object], Callable[[object], None], Callable[[str], None]]
        ] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(30)

    def submit(
        self,
        job: Callable[[Service], object],
        done: Callable[[object], None],
        failed: Callable[[str], None] | None = None,
    ) -> None:
        def execute() -> object:
            self.root.mkdir(parents=True, exist_ok=True)
            db = connect(self.root / "mycmd.sqlite3")
            try:
                return job(Service(db, self.owner))
            finally:
                db.close()

        self.pending.append((self.executor.submit(execute), done, failed or self.error.emit))
        self.busy.emit(True)

    def poll(self) -> None:
        for future, done, failed in list(self.pending):
            if future.done():
                self.pending.remove((future, done, failed))
                try:
                    result = future.result()
                except Exception as exc:
                    failed(str(exc))
                else:
                    done(result)
        self.busy.emit(bool(self.pending))

    def close(self) -> None:
        self.timer.stop()
        self.executor.shutdown(wait=True, cancel_futures=True)
