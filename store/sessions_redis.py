"""Compatibility shim — implementation lives in grok2api.store.sessions_redis."""
from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_impl = _import_module("grok2api.store.sessions_redis")
globals().update(_impl.__dict__)
_sys.modules[__name__] = _impl
