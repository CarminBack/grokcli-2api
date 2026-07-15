"""Compatibility launcher — real application lives in grok2api.app."""
from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_impl = _import_module("grok2api.app")

if __name__ == "__main__":
    _impl.main()
else:
    globals().update(_impl.__dict__)
    _sys.modules[__name__] = _impl
