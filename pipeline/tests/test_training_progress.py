"""Progress remains live inside a blocking fit and closes cleanly on errors."""

import io
import logging
import threading
import unittest

from models.training_progress import TrainingProgress


class ProgressTests(unittest.TestCase):
    def test_eta_stage_counts_and_failure(self):
        now = [0.0]
        logger = logging.getLogger("test-training-progress")
        with self.assertLogs(logger, level="INFO") as captured:
            with TrainingProgress(2, logger, stream=io.StringIO(), clock=lambda: now[0]) as progress:
                with progress.step("market/logistic fit", 100):
                    self.assertIn("ETA estimating", progress.render())
                    now[0] = 10
                self.assertIn("1/2", progress.render())
                self.assertIn("ETA ~00:00:10", progress.render())
                with progress.step("history/refit", 200):
                    now[0] = 20
            self.assertEqual(progress.completed, 2)
            self.assertIn("ETA 00:00:00", progress.render())
            self.assertFalse(progress.thread.is_alive())
            with self.assertRaisesRegex(ValueError, "fit failed"):
                with TrainingProgress(2, logger, stream=io.StringIO()) as failed:
                    with failed.step("market/fit", 100):
                        raise ValueError("fit failed")
            self.assertEqual(failed.completed, 0)
            self.assertFalse(failed.thread.is_alive())
        self.assertTrue(any("FAILED" in line for line in captured.output))

    def test_heartbeat_reports_while_fit_is_still_running(self):
        refreshed = threading.Event()
        logger = logging.getLogger("test-training-heartbeat")

        class HeartbeatProgress(TrainingProgress):
            def refresh(self):
                if threading.current_thread() is self.thread:
                    refreshed.set()

        with HeartbeatProgress(1, logger, interval=0.01) as progress:
            with progress.step("blocking estimator", 100):
                self.assertTrue(refreshed.wait(timeout=2))
                self.assertEqual(progress.completed, 0)

    def test_terminal_has_ascii_bar(self):
        class Terminal(io.StringIO):
            def isatty(self):
                return True

        stream = Terminal()
        with TrainingProgress(1, logging.getLogger(__name__), stream=stream) as progress:
            with progress.step("fit", 100):
                pass
        self.assertIn("1/1", stream.getvalue())
        self.assertIn("ETA 00:00:00", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
