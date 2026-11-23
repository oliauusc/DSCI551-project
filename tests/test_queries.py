"""Execute the shared workload queries against an in-memory SQLite fixture.

The queries are written engine-agnostic on purpose: production runs them on
MySQL through SQLAlchemy, and here on SQLite so the assertions cover the real
result columns and behavior without needing a database server.
"""
import sqlite3

import pandas as pd
import pytest

from src import query_mysql


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE institutions (
            unit_id INTEGER PRIMARY KEY,
            inst_name TEXT, city TEXT, state TEXT, control INTEGER,
            adm_rate REAL, sat_avg INTEGER,
            tuition_in_state INTEGER, tuition_out_state INTEGER,
            completion_rate_4yr REAL, median_debt REAL, median_earnings_10yr REAL
        );
        CREATE TABLE fields_of_study (
            unit_id INTEGER, cip_code TEXT, credential_level INTEGER,
            cip_desc TEXT, median_debt REAL, median_earnings_10yr REAL,
            PRIMARY KEY (unit_id, cip_code, credential_level)
        );
        INSERT INTO institutions VALUES
            (1, 'Alpha University', 'Los Angeles', 'CA', 1, 0.37, 1280,
             11500, 42000, 0.84, 21000.0, 66000.0),
            (2, 'Beta College', 'Berkeley', 'CA', 2, 0.65, 1180,
             18000, 46000, 0.78, 24500.0, 71000.0),
            (3, 'Gamma State', 'Columbus', 'OH', 1, 0.85, 1090,
             9800, 26000, 0.71, 19500.0, 52000.0),
            (4, 'Delta Institute', 'Boston', 'MA', 2, 0.22, 1450,
             24000, 55000, 0.91, 28000.0, 88000.0);
        INSERT INTO fields_of_study VALUES
            (1, '11.0101', 3, 'Computer Science', 21500.0, 88000.0),
            (1, '52.0201', 3, 'Business Administration', 21000.0, 68000.0),
            (2, '11.0101', 3, 'Computer Science', 26000.0, 92000.0),
            (2, '42.0101', 3, 'Psychology', NULL, NULL),
            (3, '13.1202', 3, 'Elementary Education', 18500.0, 44000.0),
            (4, '14.0101', 3, 'Engineering', 30000.0, 96000.0);
        """
    )
    yield connection
    connection.close()


def run_sqlite(connection, sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql_query(sql, connection, params=params or {})


def test_filtered_institutions_columns_and_filters(conn):
    sql, params = query_mysql.filtered_institutions_query(
        states=["CA", "MA"], control=2, adm_rate_min=0.3, adm_rate_max=0.9, limit=50
    )
    df = run_sqlite(conn, sql, params)
    assert list(df.columns) == query_mysql.RESULT_COLUMNS["filtered_institutions"]
    # Beta College is the only CA/MA private school with adm_rate in [0.3, 0.9].
    assert len(df) == 1
    assert df.loc[0, "inst_name"] == "Beta College"


def test_filtered_institutions_field_search(conn):
    sql, params = query_mysql.filtered_institutions_query(field_search="computer", limit=50)
    df = run_sqlite(conn, sql, params)
    assert sorted(df["unit_id"].tolist()) == [1, 2]


def test_top_fields_orders_by_earnings_and_drops_nulls(conn):
    sql, params = query_mysql.top_fields_of_study_query(limit=10)
    df = run_sqlite(conn, sql, params)
    assert list(df.columns) == query_mysql.RESULT_COLUMNS["top_fields_of_study"]
    assert df.loc[0, "median_earnings_10yr"] == 96000.0  # Engineering at Delta
    assert "Psychology" not in df["cip_desc"].tolist()  # NULL earnings excluded
    assert len(df) == 5


def test_avg_tuition_by_state_columns_and_values(conn):
    sql, params = query_mysql.avg_tuition_by_state_query()
    df = run_sqlite(conn, sql, params)
    assert list(df.columns) == query_mysql.RESULT_COLUMNS["avg_tuition_by_state"]
    ca = df[df["state"] == "CA"].iloc[0]
    assert ca["institutions"] == 2
    assert ca["avg_tuition_in_state"] == pytest.approx((11500 + 18000) / 2)


def test_completion_by_control_groups(conn):
    sql, params = query_mysql.completion_by_control_query()
    df = run_sqlite(conn, sql, params)
    assert list(df.columns) == query_mysql.RESULT_COLUMNS["completion_by_control"]
    public = df[df["control_label"] == "Public"].iloc[0]
    assert public["institutions"] == 2
    assert public["avg_completion_rate"] == pytest.approx((0.84 + 0.71) / 2)


def test_registry_matches_every_shared_query():
    assert set(query_mysql.RESULT_COLUMNS) == {
        "filtered_institutions",
        "top_fields_of_study",
        "avg_tuition_by_state",
        "completion_by_control",
    }
