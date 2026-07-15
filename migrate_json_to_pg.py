"""Compatibility wrapper — real CLI lives in scripts/migrate_json_to_pg.py."""
from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "scripts" / "migrate_json_to_pg.py"),
    run_name="__main__",
)
