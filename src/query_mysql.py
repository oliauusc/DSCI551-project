"""MySQL connection helper and the shared workload queries.

The queries use named parameters and ANSI-compatible syntax so the pytest
suite can execute them against an in-memory SQLite fixture, while production
runs against MySQL through SQLAlchemy + PyMySQL.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

from src.config import mysql_config

_ENGINE: Engine | None = None

CONTROL_LABELS: dict[int, str] = {1: "Public", 2: "Private nonprofit", 3: "Private for-profit"}


def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine for the configured MySQL database."""
    global _ENGINE
    if _ENGINE is None:
        cfg = mysql_config()
        if not cfg.is_complete:
            raise RuntimeError(
                "MySQL is not configured. Set MYSQL_USER (plus optionally "
                "MYSQL_HOST/MYSQL_PORT/MYSQL_PASSWORD/MYSQL_DATABASE) in the "
                "environment or in .streamlit/secrets.toml."
            )
        url = URL.create(
            "mysql+pymysql",
            username=cfg.user,
            password=cfg.password,
            host=cfg.host,
            port=cfg.port,
            database=cfg.database,
            query={"charset": "utf8mb4"},
        )
        _ENGINE = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
    return _ENGINE


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run one statement and return the result as a DataFrame."""
    return pd.read_sql(text(sql), get_engine(), params=params or {})


INSTITUTION_COLUMNS = [
    "unit_id",
    "inst_name",
    "city",
    "state",
    "control",
    "adm_rate",
    "sat_avg",
    "tuition_in_state",
    "tuition_out_state",
    "completion_rate_4yr",
    "median_debt",
    "median_earnings_10yr",
]


def filtered_institutions_query(
    states: list[str] | None = None,
    control: int | None = None,
    adm_rate_min: float | None = None,
    adm_rate_max: float | None = None,
    field_search: str | None = None,
    limit: int = 200,
) -> tuple[str, dict]:
    """Institutions matching the explorer filters; each filter is optional.

    `field_search` matches institutions offering any field of study whose
    description contains the given text (case-insensitive).
    """
    clauses: list[str] = []
    params: dict = {}
    if states:
        placeholders = []
        for i, state in enumerate(states):
            params[f"state_{i}"] = state
            placeholders.append(f":state_{i}")
        clauses.append(f"state IN ({', '.join(placeholders)})")
    if control is not None:
        clauses.append("control = :control")
        params["control"] = control
    if adm_rate_min is not None:
        clauses.append("adm_rate >= :adm_rate_min")
        params["adm_rate_min"] = adm_rate_min
    if adm_rate_max is not None:
        clauses.append("adm_rate <= :adm_rate_max")
        params["adm_rate_max"] = adm_rate_max
    if field_search:
        clauses.append(
            "unit_id IN (SELECT unit_id FROM fields_of_study "
            "WHERE cip_desc LIKE :field_pattern)"
        )
        params["field_pattern"] = f"%{field_search}%"
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        f"SELECT {', '.join(INSTITUTION_COLUMNS)} FROM institutions"
        f"{where} ORDER BY inst_name LIMIT :limit"
    )
    params["limit"] = int(limit)
    return sql, params


def top_fields_of_study_query(limit: int = 20) -> tuple[str, dict]:
    sql = """
SELECT i.inst_name, i.state, f.cip_desc, f.credential_level,
       f.median_debt, f.median_earnings_10yr
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.median_earnings_10yr IS NOT NULL
ORDER BY f.median_earnings_10yr DESC
LIMIT :limit"""
    return sql.strip(), {"limit": int(limit)}


def avg_tuition_by_state_query() -> tuple[str, dict]:
    sql = """
SELECT state,
       COUNT(*) AS institutions,
       AVG(tuition_in_state) AS avg_tuition_in_state,
       AVG(tuition_out_state) AS avg_tuition_out_of_state
FROM institutions
WHERE state IS NOT NULL
GROUP BY state
ORDER BY avg_tuition_in_state DESC"""
    return sql.strip(), {}


def completion_by_control_query() -> tuple[str, dict]:
    sql = """
SELECT CASE control WHEN 1 THEN 'Public'
                    WHEN 2 THEN 'Private nonprofit'
                    WHEN 3 THEN 'Private for-profit'
                    ELSE 'Unknown' END AS control_label,
       COUNT(*) AS institutions,
       AVG(completion_rate_4yr) AS avg_completion_rate,
       AVG(median_debt) AS avg_median_debt,
       AVG(median_earnings_10yr) AS avg_median_earnings_10yr
FROM institutions
WHERE control IN (1, 2, 3)
GROUP BY control"""
    return sql.strip(), {}


# Expected result columns, keyed by query name. Tests execute every query
# against a SQLite fixture and assert these columns come back in this order.
RESULT_COLUMNS: dict[str, list[str]] = {
    "filtered_institutions": INSTITUTION_COLUMNS,
    "top_fields_of_study": [
        "inst_name",
        "state",
        "cip_desc",
        "credential_level",
        "median_debt",
        "median_earnings_10yr",
    ],
    "avg_tuition_by_state": [
        "state",
        "institutions",
        "avg_tuition_in_state",
        "avg_tuition_out_of_state",
    ],
    "completion_by_control": [
        "control_label",
        "institutions",
        "avg_completion_rate",
        "avg_median_debt",
        "avg_median_earnings_10yr",
    ],
}
