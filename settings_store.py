"""Compatibility shim — implementation lives in grok2api.admin.settings_store."""
from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_impl = _import_module("grok2api.admin.settings_store")
_sys.modules[__name__] = _impl
