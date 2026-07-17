"""Compatibility shim — implementation lives in grok2api.pool.auth."""
from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_impl = _import_module("grok2api.pool.auth")
_sys.modules[__name__] = _impl
