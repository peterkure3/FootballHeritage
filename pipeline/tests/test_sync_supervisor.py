"""The supervisor must replace a destination connection lost inside a batch."""

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sync import scheduler


class SupervisorTests(unittest.TestCase):
    def test_reconnects_when_batch_handles_a_closed_destination(self):
        local, first_remote, recovered_remote = MagicMock(), MagicMock(), MagicMock()
        local.closed = first_remote.closed = recovered_remote.closed = False
        local.cursor.return_value.__enter__.return_value.fetchone.return_value = (True,)
        stop = threading.Event()
        stop.wait = MagicMock()
        destinations = []

        def batch(_local, remote):
            destinations.append(remote)
            if len(destinations) == 1:
                remote.closed = True
                return {"outcome": "retry_or_dead_letter", "count": 1}
            stop.set()
            return {"outcome": "published", "count": 1}

        with tempfile.TemporaryDirectory() as folder:
            env_file = Path(folder) / ".env.sync"
            env_file.write_text("", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {
                        "SYNC_LOCAL_DATABASE_URL": "local-test",
                        "SYNC_NEON_DATABASE_URL": "remote-test",
                        "SYNC_MODEL_VERSION": "test-model",
                    },
                ),
                patch("sys.argv", ["sync.scheduler", "--env", str(env_file)]),
                patch.object(scheduler.threading, "Event", return_value=stop),
                patch.object(scheduler.signal, "signal"),
                patch.object(
                    scheduler,
                    "connect",
                    side_effect=[local, first_remote, recovered_remote],
                ) as connector,
                patch.object(scheduler, "project", return_value={"processed": 0}),
                patch.object(scheduler, "run_batch", side_effect=batch),
                patch("builtins.print"),
            ):
                self.assertEqual(scheduler.main(), 0)
        self.assertEqual(destinations, [first_remote, recovered_remote])
        self.assertEqual(connector.call_count, 3)
        recovered_remote.close.assert_called_once()
