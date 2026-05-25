"""Local pickle cache for API responses.

Each cached call writes its return value to a file in ``cache/`` keyed by a
hash of the function name + arguments. On subsequent calls within ``ttl_seconds``
the cached value is returned instead of hitting the network.
"""
import functools
import hashlib
import pickle
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.pkl"


def cached(ttl_seconds: int):
    """Decorator: pickle the return value to disk and reuse it until TTL expires."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__module__}.{fn.__name__}|{args}|{sorted(kwargs.items())}"
            path = _cache_path(key)
            if path.exists() and (time.time() - path.stat().st_mtime) < ttl_seconds:
                with path.open("rb") as f:
                    return pickle.load(f)
            result = fn(*args, **kwargs)
            with path.open("wb") as f:
                pickle.dump(result, f)
            return result
        return wrapper
    return decorator
