import os
import unittest
from unittest.mock import patch

from models.training_resources import training_threads


class TrainingResourcesTests(unittest.TestCase):
    def test_thread_environment_restored_on_success_and_failure(self):
        with patch.dict(os.environ, {"OMP_NUM_THREADS": "7"}):
            with training_threads(2):
                self.assertEqual(os.environ["OMP_NUM_THREADS"], "2")
            self.assertEqual(os.environ["OMP_NUM_THREADS"], "7")
            with self.assertRaisesRegex(RuntimeError, "fit failed"):
                with training_threads(3):
                    raise RuntimeError("fit failed")
            self.assertEqual(os.environ["OMP_NUM_THREADS"], "7")

    def test_unset_environment_and_invalid_budget(self):
        with patch.dict(os.environ):
            os.environ.pop("OMP_NUM_THREADS", None)
            with training_threads(2):
                self.assertEqual(os.environ["OMP_NUM_THREADS"], "2")
            self.assertNotIn("OMP_NUM_THREADS", os.environ)
            with self.assertRaises(ValueError):
                with training_threads(0):
                    pass


if __name__ == "__main__":
    unittest.main()
