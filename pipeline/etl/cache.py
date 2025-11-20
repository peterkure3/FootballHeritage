"""Simple JSON file-based cache helpers for API fetchers."""
from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from config import CACHE_DIR, CACHE_ENABLED, CACHE_BYPASS
from etl.utils import ensure_dir, setup_logger

logger = setup_logger(__name__)


def _cache_file(namespace: str, key_hash: str) -> Path:
    return CACHE_DIR / namespace / f"{key_hash}.json"


def _serialize_key(parts: Dict[str, Any]) -> str:
    normalized = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_cache(namespace: str, key_parts: Dict[str, Any], ttl_seconds: int) -> Optional[Any]:
    """Return cached payload if enabled and not expired."""
    if not CACHE_ENABLED or CACHE_BYPASS or ttl_seconds <= 0:
        return None

    cache_path = _cache_file(namespace, _serialize_key(key_parts))
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            payload_wrapper = json.load(cache_file)

        cached_epoch = payload_wrapper.get("cached_epoch")
        if cached_epoch is None:
            return None

        if time.time() - cached_epoch > ttl_seconds:
            cache_path.unlink(missing_ok=True)
            return None

        return payload_wrapper.get("payload")
    except Exception as exc:  # pragma: no cover - best effort cleanup
        logger.warning("Failed to read cache %s/%s (%s)", namespace, key_parts, exc)
        try:
            cache_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def store_cache(namespace: str, key_parts: Dict[str, Any], payload: Any) -> None:
    """Persist payload to cache if enabled."""
    if not CACHE_ENABLED or CACHE_BYPASS:
        return

    cache_path = _cache_file(namespace, _serialize_key(key_parts))
    ensure_dir(cache_path.parent)

    wrapper = {
        "cached_epoch": time.time(),
        "payload": payload,
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as cache_file:
            json.dump(wrapper, cache_file)
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Failed to write cache %s/%s (%s)", namespace, key_parts, exc)
