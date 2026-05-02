"""Central configuration: DB path and data directory from environment."""

from __future__ import annotations

import os
from pathlib import Path


def get_db_path() -> str:
    """Return the DuckDB database path.

    Reads AEGIS_DB_PATH env var; falls back to 'aegis.duckdb' for local dev.
    On Fly.io this should be '/data/aegis.duckdb' (persistent volume).
    """
    return os.environ.get("AEGIS_DB_PATH", "aegis.duckdb")


def get_data_dir() -> Path:
    """Return the data directory for JSONL files.

    Reads AEGIS_DATA_DIR env var; falls back to 'data/aegis' for local dev.
    On Fly.io this should be '/data/aegis' (persistent volume).
    """
    return Path(os.environ.get("AEGIS_DATA_DIR", "data/aegis"))
