"""Streamlit explorer for the College Scorecard MySQL database.

Run from the repo root:  streamlit run app/streamlit_app.py
Credentials come from the environment or .streamlit/secrets.toml (see
.streamlit/secrets.example.toml). If MySQL is unreachable, the app shows a
setup message instead of a stack trace. All results come from live queries.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from src import query_mysql
from src.query_mysql import CONTROL_LABELS

st.set_page_config(page_title="College Scorecard Explorer", page_icon="🎓", layout="wide")


@st.cache_resource(show_spinner=False)
def _engine():
    return query_mysql.get_engine()


@st.cache_data(ttl=600, show_spinner=False)
def _states():
    df = query_mysql.run_query(
        "SELECT DISTINCT state FROM institutions WHERE state IS NOT NULL ORDER BY state"
    )
    return df["state"].tolist()


def _setup_error(exc: Exception) -> None:
    st.error(
        "Could not reach the College Scorecard MySQL database. Make sure the "
        "server is running and credentials are set in `.streamlit/secrets.toml` "
        "or environment variables (see `.streamlit/secrets.example.toml`).\n\n"
        f"Details: `{exc}`"
    )


st.title("College Scorecard Explorer")
st.caption(
    "Institution and field-of-study data from the U.S. Department of Education, "
    "served live from MySQL."
)

try:
    _engine()
    state_options = _states()
except Exception as exc:  # missing credentials or unreachable server
    _setup_error(exc)
    st.stop()

with st.sidebar:
    st.header("Filters")
    selected_states = st.multiselect("State", state_options)
    ownership = st.selectbox("Ownership", ["All", *CONTROL_LABELS.values()])
    adm_rate_pct = st.slider("Admission rate (%)", 0, 100, (0, 100))
    field_search = st.text_input("Field of study contains", placeholder="e.g. Computer Science")

control = next((code for code, label in CONTROL_LABELS.items() if label == ownership), None)

sql, params = query_mysql.filtered_institutions_query(
    states=selected_states or None,
    control=control,
    adm_rate_min=adm_rate_pct[0] / 100,
    adm_rate_max=adm_rate_pct[1] / 100,
    field_search=field_search.strip() or None,
    limit=300,
)

try:
    results = query_mysql.run_query(sql, params)
except Exception as exc:
    _setup_error(exc)
    st.stop()

st.metric("Matching institutions", f"{len(results):,}")

if results.empty:
    st.info(
        "No institutions match these filters — try widening the admission-rate "
        "range or clearing the field-of-study filter."
    )
else:
    st.dataframe(results, use_container_width=True, hide_index=True)
    st.subheader("Average published tuition by ownership (filtered set)")
    chart_data = (
        results.assign(ownership=results["control"].map(CONTROL_LABELS))
        .groupby("ownership")[["tuition_in_state", "tuition_out_state"]]
        .mean()
        .rename(
            columns={
                "tuition_in_state": "In-state",
                "tuition_out_state": "Out-of-state",
            }
        )
    )
    st.bar_chart(chart_data)
