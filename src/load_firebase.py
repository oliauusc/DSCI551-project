"""Upload a small denormalized subset of the MySQL data to Firestore.

One document per institution (document ID = UNITID) with its top fields of
study embedded, so a client reads a full school profile in a single fetch.

Usage (from the repo root):
  python -m src.load_firebase --limit 200

Credentials: the FIREBASE_SERVICE_ACCOUNT environment variable, or the
[firebase] service_account_path entry in .streamlit/secrets.toml
(see .streamlit/secrets.example.toml).
"""
from __future__ import annotations

import argparse

import pandas as pd

from src import query_mysql
from src.config import firebase_service_account_path

DEFAULT_COLLECTION = "institutions"


def init_firebase(service_account_path=None, app_name: str = "college-scorecard"):
    """Initialize (or reuse) the Firebase admin app; returns the app."""
    import firebase_admin
    from firebase_admin import credentials

    if service_account_path is None:
        service_account_path = firebase_service_account_path()
    if service_account_path is None:
        raise RuntimeError(
            "Firebase service-account path is not configured. Set "
            "FIREBASE_SERVICE_ACCOUNT or [firebase] service_account_path in "
            ".streamlit/secrets.toml (see .streamlit/secrets.example.toml)."
        )
    try:
        return firebase_admin.get_app(name=app_name)
    except ValueError:
        cred = credentials.Certificate(str(service_account_path))
        return firebase_admin.initialize_app(cred, name=app_name)


def _json_safe(row: pd.Series) -> dict:
    """Convert one DataFrame row to a Firestore-friendly dict (NaN -> None)."""
    return {
        key: None if pd.isna(value) else value.item() if hasattr(value, "item") else value
        for key, value in row.items()
    }


def build_documents(limit: int | None = None) -> list[dict]:
    """Build one denormalized document per institution, top fields embedded."""
    columns = (
        "SELECT unit_id, inst_name, city, state, control, adm_rate, "
        "tuition_in_state, tuition_out_state, median_debt, median_earnings_10yr "
        "FROM institutions ORDER BY inst_name"
    )
    params: dict = {}
    if limit is not None:
        columns += " LIMIT :limit"
        params["limit"] = int(limit)
    institutions = query_mysql.run_query(columns, params)

    fields = query_mysql.run_query(
        """
        SELECT unit_id, cip_desc, credential_level, median_earnings_10yr
        FROM fields_of_study
        WHERE median_earnings_10yr IS NOT NULL
        ORDER BY unit_id, median_earnings_10yr DESC
        """
    )
    top_fields = fields.groupby("unit_id", sort=False).head(3)

    docs = []
    for row in institutions.itertuples(index=False):
        doc = _json_safe(pd.Series(row._asdict()))
        doc["top_fields_of_study"] = [
            _json_safe(pd.Series(field_row._asdict()).drop(labels=["unit_id"]))
            for field_row in top_fields[top_fields["unit_id"] == row.unit_id].itertuples(index=False)
        ]
        docs.append(doc)
    return docs


def upload_documents(
    docs: list[dict],
    collection: str = DEFAULT_COLLECTION,
    batch_size: int = 450,
    app=None,
) -> int:
    """Write documents in batches (Firestore caps 500 writes per batch)."""
    from firebase_admin import firestore

    client = firestore.client(app) if app else firestore.client()
    uploaded = 0
    for start in range(0, len(docs), batch_size):
        batch = client.batch()
        for doc in docs[start : start + batch_size]:
            batch.set(client.collection(collection).document(str(doc["unit_id"])), doc)
        batch.commit()
        uploaded += len(docs[start : start + batch_size])
    return uploaded


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="max institutions to upload")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args(argv)

    app = init_firebase()
    docs = build_documents(limit=args.limit)
    uploaded = upload_documents(docs, collection=args.collection, app=app)
    print(f"Uploaded {uploaded} institution documents to collection {args.collection!r}.")


if __name__ == "__main__":
    main()
