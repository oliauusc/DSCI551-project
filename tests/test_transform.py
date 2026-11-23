"""Tests for the cleaning/validation helpers (no database required)."""
import pandas as pd
import pytest

from src import transform


def _institution_frame(**overrides) -> pd.DataFrame:
    data = {
        "UNITID": [100200, 100300, 100400],
        "INSTNM": ["Alpha College", "Beta Institute", "Gamma State"],
        "CITY": ["Tuscaloosa", "Birmingham", "Normal"],
        "STABBR": ["al", "AL", "Al"],
        "ZIP": ["35487", "35203", "35762"],
        "CONTROL": [1, 2, 1],
        "ADM_RATE": ["0.33", "0.75", "0.59"],
        "SAT_AVG": ["1140", "PrivacySuppressed", "990"],
        "TUITIONFEE_IN": ["10700", "20400", "PrivacySuppressed"],
        "C150_4": ["0.59", "0.66", "0.41"],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_convert_suppressed_replaces_marker_and_null_strings():
    df = pd.DataFrame({"a": ["PrivacySuppressed", "5"], "b": ["NULL", "keep"]})
    out = transform.convert_suppressed(df)
    assert pd.isna(out.loc[0, "a"])
    assert pd.isna(out.loc[0, "b"])
    assert out.loc[1, "a"] == "5"
    assert out.loc[1, "b"] == "keep"


def test_clean_institutions_converts_types_and_suppression():
    df = transform.clean_institutions(_institution_frame())
    assert str(df["unit_id"].dtype) == "Int64"
    assert df["state"].tolist() == ["AL", "AL", "AL"]
    assert df.loc[0, "adm_rate"] == pytest.approx(0.33)
    assert pd.isna(df.loc[1, "sat_avg"])
    assert pd.isna(df.loc[2, "tuition_in_state"])


def test_clean_institutions_requires_unique_unit_ids():
    with pytest.raises(ValueError, match="duplicate natural-key"):
        transform.clean_institutions(_institution_frame(UNITID=[100200, 100200, 100400]))


def test_clean_fields_of_study_enforces_composite_key():
    raw = pd.DataFrame(
        {
            "UNITID": [100200, 100200, 100300],
            "CIPCODE": ["11.0101", "11.0101", "52.0201"],
            "CREDENTIAL_LEVEL": [3, 5, 3],  # level differs, so the key is unique
            "CIPDESC": ["Computer Science", "Computer Science", "Business Administration"],
            "DEBT_MEDIAN": ["13500", "PrivacySuppressed", "PrivacySuppressed"],
            "EARN_MEDIAN_10YR": ["86400", "PrivacySuppressed", "PrivacySuppressed"],
        }
    )
    cleaned = transform.clean_fields_of_study(raw)
    assert len(cleaned) == 3
    assert pd.isna(cleaned.loc[1, "median_earnings_10yr"])

    raw.loc[1, "CREDENTIAL_LEVEL"] = 3  # now collides with row 0
    with pytest.raises(ValueError, match="duplicate natural-key"):
        transform.clean_fields_of_study(raw)


def test_missing_source_columns_reports_unmatched_canonical_names():
    df = _institution_frame().drop(columns=["ADM_RATE", "SAT_AVG"])
    missing = transform.missing_source_columns(df, transform.INSTITUTION_FIELDS)
    assert "adm_rate" in missing
    assert "sat_avg" in missing
    assert "unit_id" not in missing
