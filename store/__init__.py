"""Compatibility package — implementation lives in grok2api.store."""
from __future__ import annotations

from importlib import import_module as _import_module

_impl = _import_module("grok2api.store")

for _name in getattr(_impl, "__all__", ()):  # pragma: no cover - currently empty
    globals()[_name] = getattr(_impl, _name)

# Export public helpers from grok2api.store while keeping this root package's
# __path__, so imports like `store.redis_client` load wrapper modules that alias
# to the real `grok2api.store.redis_client` module instead of duplicating state.
for _name, _value in _impl.__dict__.items():
    if not _name.startswith("__") or _name in {"__doc__", "__all__"}:
        globals()[_name] = _value
