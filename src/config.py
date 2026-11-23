"""Configuration loading for the College Scorecard project.

Credentials are never stored in this repo. Values are resolved in order:
1. Environment variables (optionally loaded from a local `.env` file).
2. Streamlit secrets (`.streamlit/secrets.toml`) when running under Streamlit.

Every value has a placeholder default so importing this module never raises;
the connection helpers surface a clear error when required values are missing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(REPO_ROOT / ".env")

DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_CLEAN_DIR = REPO_ROOT / "data" / "cleaned"


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def is_complete(self) -> bool:
        # Without a user (and a database) no connection can succeed.
        return bool(self.user) and bool(self.database)


def _streamlit_secret(section: str, key: str) -> str | None:
    """Read a value from .streamlit/secrets.toml if Streamlit is available."""
    try:
        import streamlit as st

        return st.secrets[section][key]
    except Exception:
        return None


def _setting(env_name: str, section: str, key: str, default: str = "") -> str:
    return os.environ.get(env_name) or _streamlit_secret(section, key) or default


def mysql_config() -> MySQLConfig:
    port = _setting("MYSQL_PORT", "mysql", "port", "3306")
    return MySQLConfig(
        host=_setting("MYSQL_HOST", "mysql", "host", "127.0.0.1"),
        port=int(port),
        user=_setting("MYSQL_USER", "mysql", "user"),
        password=_setting("MYSQL_PASSWORD", "mysql", "password"),
        database=_setting("MYSQL_DATABASE", "mysql", "database", "college_scorecard"),
    )


def firebase_service_account_path() -> Path | None:
    raw = _setting("FIREBASE_SERVICE_ACCOUNT", "firebase", "service_account_path")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path
