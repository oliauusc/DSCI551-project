"""Cleaning and validation for College Scorecard CSVs.

Source conventions handled here:
- Suppressed values appear as the literal string "PrivacySuppressed"; they
  become NaN in pandas and NULL in MySQL.
- Source column names drift between yearly releases, so each canonical column
  lists candidate source names (first match wins). The maps target the
  2023-24 release; adjust them if the team's release differs.
"""
from __future__ import annotations

import pandas as pd

SUPPRESSED_TOKEN = "PrivacySuppressed"
NULL_TOKENS = (SUPPRESSED_TOKEN, "NULL")

# canonical column -> candidate source columns, in preference order
INSTITUTION_FIELDS: dict[str, tuple[str, ...]] = {
    "unit_id": ("UNITID",),
    "inst_name": ("INSTNM",),
    "city": ("CITY",),
    "state": ("STABBR",),
    "zip_code": ("ZIP",),
    "accreditation": ("ACCREDAGENCY",),
    "inst_url": ("INSTURL",),
    "net_price_url": ("NPCURL",),
    # newer releases renamed CONTROL -> SCH_TYPE with the same 1/2/3 encoding
    "control": ("CONTROL", "SCH_TYPE"),
    "locale": ("LOCALE",),
    "carnegie_basic": ("CC_BASIC",),
    "adm_rate": ("ADM_RATE", "ADM_RATE_ALL"),
    "sat_avg": ("SAT_AVG",),
    "undergrad_size": ("UGDS",),
    "tuition_in_state": ("TUITIONFEE_IN",),
    "tuition_out_state": ("TUITIONFEE_OUT",),
    "avg_faculty_salary": ("AVGFACSAL",),
    "pct_fulltime_faculty": ("PFTFAC",),
    "completion_rate_4yr": ("C150_4",),
    "retention_rate_ft": ("RET_FT4",),
    "median_debt": ("DEBT_MD", "GRAD_DEBT_MD"),
    "median_earnings_10yr": ("MD_EARN_WNE_P10", "EARN_MD_10YR"),
}

FIELD_OF_STUDY_FIELDS: dict[str, tuple[str, ...]] = {
    "unit_id": ("UNITID",),
    "cip_code": ("CIPCODE",),
    "credential_level": ("CREDENTIAL_LEVEL",),
    "cip_desc": ("CIPDESC",),
    "median_debt": ("DEBT_MEDIAN", "DEBT_MD"),
    "median_earnings_10yr": ("EARN_MEDIAN_10YR", "MD_EARN_WNE_P10"),
}

INSTITUTION_INT_COLUMNS = (
    "unit_id",
    "control",
    "locale",
    "carnegie_basic",
    "undergrad_size",
    "tuition_in_state",
    "tuition_out_state",
    "avg_faculty_salary",
)
INSTITUTION_FLOAT_COLUMNS = (
    "adm_rate",
    "sat_avg",
    "pct_fulltime_faculty",
    "completion_rate_4yr",
    "retention_rate_ft",
    "median_debt",
    "median_earnings_10yr",
)
FOS_INT_COLUMNS = ("unit_id", "credential_level")
FOS_FLOAT_COLUMNS = ("median_debt", "median_earnings_10yr")


def convert_suppressed(df: pd.DataFrame) -> pd.DataFrame:
    """Replace the suppression marker and literal 'NULL' strings with NaN."""
    out = df.copy()
    text_columns = out.select_dtypes(include=["object", "string"]).columns
    out[text_columns] = out[text_columns].mask(out[text_columns].isin(NULL_TOKENS))
    return out


def missing_source_columns(df: pd.DataFrame, fields: dict[str, tuple[str, ...]]) -> list[str]:
    """Canonical columns whose source names appear nowhere in `df.columns`."""
    return [
        canonical
        for canonical, candidates in fields.items()
        if not any(source in df.columns for source in candidates)
    ]


def _select_fields(df: pd.DataFrame, fields: dict[str, tuple[str, ...]]) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for canonical, candidates in fields.items():
        for source in candidates:
            if source in df.columns:
                rename[source] = canonical
                break
    out = df[list(rename)].rename(columns=rename)
    for canonical in fields:
        if canonical not in out.columns:
            out[canonical] = pd.NA  # keep the schema stable if a release drops a column
    return out


def validate_unique_key(df: pd.DataFrame, keys: list[str], table_name: str) -> pd.DataFrame:
    """Raise unless the natural-key columns are fully populated and unique."""
    null_rows = df[keys].isna().any(axis=1)
    if null_rows.any():
        raise ValueError(
            f"{table_name}: {int(null_rows.sum())} rows have NULL natural-key columns {keys}"
        )
    dup_mask = df.duplicated(subset=keys, keep=False)
    if dup_mask.any():
        examples = df.loc[dup_mask, keys].drop_duplicates().head(5).to_dict("records")
        raise ValueError(f"{table_name}: duplicate natural-key values for {keys}: {examples}")
    return df


def clean_institutions(raw: pd.DataFrame) -> pd.DataFrame:
    df = _select_fields(convert_suppressed(raw), INSTITUTION_FIELDS)
    for col in INSTITUTION_INT_COLUMNS + INSTITUTION_FLOAT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["state"] = df["state"].astype("string").str.strip().str.upper()
    df["unit_id"] = df["unit_id"].astype("Int64")
    df["control"] = df["control"].astype("Int64")
    df = df.dropna(subset=["unit_id"])
    validate_unique_key(df, ["unit_id"], "institutions")
    return df[list(INSTITUTION_FIELDS)].reset_index(drop=True)


def clean_fields_of_study(raw: pd.DataFrame) -> pd.DataFrame:
    df = _select_fields(convert_suppressed(raw), FIELD_OF_STUDY_FIELDS)
    for col in FOS_INT_COLUMNS + FOS_FLOAT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["unit_id"] = df["unit_id"].astype("Int64")
    df["credential_level"] = df["credential_level"].astype("Int64")
    df["cip_code"] = df["cip_code"].astype("string").str.strip()
    df = df.dropna(subset=["unit_id", "cip_code", "credential_level"])
    validate_unique_key(df, ["unit_id", "cip_code", "credential_level"], "fields_of_study")
    return df[list(FIELD_OF_STUDY_FIELDS)].reset_index(drop=True)
