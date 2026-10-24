"""Explicit CPU budgets for offline model training and evaluation."""

from contextlib import contextmanager
import os

from threadpoolctl import threadpool_limits


@contextmanager
def training_threads(threads: int):
    """Avoid automatic Windows physical-core discovery and bound loaded runtimes.

    The environment setting is also checked by scikit-learn's OpenMP helper
    after import. threadpoolctl alone does not bypass Joblib's PowerShell probe.
    This process-scoped context is for sequential offline training, not API jobs.
    """
    if threads < 1:
        raise ValueError("Training threads must be positive")
    previous = os.environ.get("OMP_NUM_THREADS")
    os.environ["OMP_NUM_THREADS"] = str(threads)
    try:
        with threadpool_limits(limits=threads):
            yield
    finally:
        if previous is None:
            os.environ.pop("OMP_NUM_THREADS", None)
        else:
            os.environ["OMP_NUM_THREADS"] = previous
