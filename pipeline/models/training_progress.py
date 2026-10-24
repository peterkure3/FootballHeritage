"""Live progress for blocking estimator fits, without an extra dependency."""

from contextlib import contextmanager
import logging
import shutil
import sys
import threading
import time


class TrainingProgress:
    """Report completed stages; ETA is approximate, never invented within a fit."""

    def __init__(self, total: int, logger: logging.Logger, stream=None,
                 interval: float = None, clock=time.monotonic) -> None:
        self.total = total
        self.logger = logger
        self.stream = stream if stream is not None else sys.stderr
        self.interactive = self.stream.isatty()
        self.interval = interval if interval is not None else (1 if self.interactive else 30)
        self.clock = clock
        self.completed = 0
        self.started = self.clock()
        self.stage_started = self.started
        self.finished_seconds = 0.0
        self.label = "starting"
        self.samples = 0
        self.lock = threading.RLock()
        self.stopped = threading.Event()
        self.thread = None

    @staticmethod
    def duration(seconds: float) -> str:
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def render(self) -> str:
        with self.lock:
            now = self.clock()
            stage_elapsed = now - self.stage_started
            eta = "estimating"
            if self.completed == self.total:
                eta = "00:00:00"
            elif self.completed:
                remaining = self.finished_seconds / self.completed * (self.total - self.completed) - stage_elapsed
                if remaining > 0:
                    eta = "~" + self.duration(remaining)
            filled = int(20 * self.completed / self.total)
            return (f"Expert selection [{'#' * filled}{'-' * (20 - filled)}] "
                    f"{self.completed}/{self.total} | {self.label} rows={self.samples:,} | "
                    f"elapsed {self.duration(now - self.started)} | "
                    f"step {self.duration(stage_elapsed)} | ETA {eta}")

    def refresh(self) -> None:
        message = self.render()
        if self.interactive:
            width = max(40, shutil.get_terminal_size(fallback=(120, 24)).columns - 1)
            if len(message) > width:
                # Keep elapsed/ETA visible instead of wrapping or truncating them.
                eta = message.rsplit("ETA ", 1)[1]
                filled = int(10 * self.completed / self.total)
                message = (f"[{'#' * filled}{'-' * (10 - filled)}] {self.completed}/{self.total} elapsed "
                           f"{self.duration(self.clock() - self.started)} ETA {eta} | {self.label}")
            self.stream.write("\r" + message[:width].ljust(width))
            self.stream.flush()
        else:
            self.logger.info(message)

    def _heartbeat(self) -> None:
        while not self.stopped.wait(self.interval):
            self.refresh()

    def __enter__(self):
        self.started = self.stage_started = self.clock()
        self.thread = threading.Thread(target=self._heartbeat, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stopped.set()
        self.thread.join()
        if exc_type:
            with self.lock:
                self.label += " FAILED"
        self.refresh()
        if self.interactive:
            self.stream.write("\n")
            self.stream.flush()

    @contextmanager
    def step(self, label: str, samples: int):
        with self.lock:
            self.label, self.samples = label, samples
            self.stage_started = self.clock()
        self.refresh()
        yield
        with self.lock:
            self.finished_seconds += self.clock() - self.stage_started
            self.completed += 1
            self.stage_started = self.clock()
        self.refresh()
