# College Scorecard Database — DSCI 551 Final Project

Two-person course project that turns U.S. Department of Education
[College Scorecard](https://collegescorecard.ed.gov/data) files into a queryable
MySQL database, compares index designs with `EXPLAIN` / `EXPLAIN ANALYZE`,
mirrors a small denormalized subset into Firebase Firestore, and serves it all
through a Streamlit explorer.

## Architecture

```
Google Drive (shared CSVs, gitignored)
        |  copied into data/raw/
        v
src/transform.py  ->  cleaned DataFrames (PrivacySuppressed -> NULL, typed columns, key checks)
        |
        +--> MySQL 8.0   sql/01 schema, sql/02 integrity checks, sql/03 workload queries,
        |                sql/04 index experiments (src/load_mysql.py does the loading)
        +--> Firebase Firestore (src/load_firebase.py: one doc per institution)
        +--> Streamlit app (app/streamlit_app.py) reads MySQL live
```

## Repository layout

```
app/          Streamlit explorer (streamlit_app.py) + pages/
notebook/     Final project notebook (execution, evidence, interpretation)
sql/          01 schema, 02 integrity checks, 03 workload queries, 04 index experiments
src/          Reusable pipeline code: config, transform, load_mysql, query_mysql, load_firebase
tests/        pytest suite (no database required)
docs/         Data dictionary for the loaded schema
.streamlit/   secrets.example.toml (template — real secrets.toml is gitignored)
```

## Prerequisites

- Python 3.11+
- MySQL 8.0+ (`EXPLAIN ANALYZE` needs 8.0.18+, `CHECK` constraints 8.0.16+)
- A Firebase project (optional — only for the Firestore step)
- Access to the team's shared Google Drive folder with the chosen Scorecard release

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.example.toml .streamlit/secrets.toml   # then fill in real values
```

Credentials live in `.streamlit/secrets.toml` or environment variables
(`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`,
`FIREBASE_SERVICE_ACCOUNT`). Nothing real is ever committed.

## Data placement

Copy the shared CSVs from Google Drive into `data/raw/` (gitignored):

```
data/raw/MERGED2023-24_PP.csv        # institution-level file from the team's release
data/raw/FieldOfStudy2023-24.csv     # field-of-study file (match the release's name)
```

`data/raw/` and `data/cleaned/` never enter Git; every teammate downloads their
own copy from Drive.

## Build the MySQL database

```bash
mysql -u root -p < sql/01_create_schema.sql
python -m src.load_mysql institutions     --raw data/raw/MERGED2023-24_PP.csv
python -m src.load_mysql fields_of_study  --raw data/raw/FieldOfStudy2023-24.csv
mysql -u root -p college_scorecard < sql/02_integrity_checks.sql   # violation counts should all be 0
```

Then run `sql/03_workload_queries.sql` for the analytical workload and
`sql/04_index_experiments.sql` for the before/after index comparison. Save
EXPLAIN outputs under `results/` (gitignored).

## Run the notebook

```bash
jupyter lab notebook/DSCI_551_Final_Project_Notebook.ipynb   # or open it in VS Code
```

The notebook executes the pipeline end to end and records evidence; all
reusable logic lives in `src/` so the notebook stays readable.

## Run Streamlit

```bash
streamlit run app/streamlit_app.py
```

If MySQL is unreachable or credentials are missing, the app shows a friendly
setup message instead of a stack trace.

## Firebase credentials

- Environment variable: `FIREBASE_SERVICE_ACCOUNT=/path/to/serviceAccount.json`, **or**
- `.streamlit/secrets.toml` -> `[firebase] service_account_path = "..."`

Then load the subset: `python -m src.load_firebase --limit 200`.
The JSON key file itself is gitignored (`*serviceAccount*.json`).

## Team workflow

- `main` is the stable branch; work happens on short feature branches:
  `mysql-load`, `firebase`, `streamlit`, `analysis`.
- Reusable logic goes in `src/`; the notebook stays focused on execution,
  evidence, and interpretation.
- Generated data, figures, EXPLAIN plans (`results/`), and credentials stay out of Git.
- Before committing: `pytest` passes, and `git status` shows no data or secret
  files staged.
- Open small PRs; the teammate reviews before merge. Commit messages in
  imperative mood ("Add admission-rate index experiment").
