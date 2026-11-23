# Data Dictionary

Schema loaded from the U.S. Department of Education College Scorecard release
shared by the team (column names target the **2023-24** release).
`src/transform.py` maps source columns to the canonical names below; where
releases differ, each canonical column lists candidate source names and the
first match wins — so a new release usually only needs a mapping tweak.

## Suppression convention

The raw files mark suppressed values with the literal string
`PrivacySuppressed`. All cleaning paths (`src/transform.py`) convert it — and
literal `NULL` strings — to real NULLs, which is what the database and the app
expect. Never load the raw string into MySQL.

## `institutions`

| Column | MySQL type | Source column(s) | Description |
|---|---|---|---|
| `unit_id` | INT, PK | `UNITID` | IPEDS UNITID; the natural key. |
| `inst_name` | VARCHAR(255) | `INSTNM` | Institution name. |
| `city` | VARCHAR(120) | `CITY` | City. |
| `state` | CHAR(2) | `STABBR` | 2-letter state code, uppercased on load. |
| `zip_code` | VARCHAR(10) | `ZIP` | ZIP code. |
| `accreditation` | VARCHAR(255) | `ACCREDAGENCY` | Accrediting agency. |
| `inst_url` | VARCHAR(255) | `INSTURL` | Homepage URL. |
| `net_price_url` | VARCHAR(255) | `NPCURL` | Net price calculator URL. |
| `control` | TINYINT | `CONTROL` (fallback `SCH_TYPE`) | 1 = Public, 2 = Private nonprofit, 3 = Private for-profit. |
| `locale` | SMALLINT | `LOCALE` | Locale code (11 = City large … 43 = Rural remote). |
| `carnegie_basic` | SMALLINT | `CC_BASIC` | Carnegie basic classification code. |
| `adm_rate` | DECIMAL(5,4) | `ADM_RATE` (fallback `ADM_RATE_ALL`) | Admission rate, 0–1. |
| `sat_avg` | SMALLINT | `SAT_AVG` | Average SAT equivalent. |
| `undergrad_size` | INT | `UGDS` | Undergraduate enrollment. |
| `tuition_in_state` | MEDIUMINT UNSIGNED | `TUITIONFEE_IN` | Published in-state tuition & fees (USD). |
| `tuition_out_state` | MEDIUMINT UNSIGNED | `TUITIONFEE_OUT` | Published out-of-state tuition & fees (USD). |
| `avg_faculty_salary` | MEDIUMINT UNSIGNED | `AVGFACSAL` | Average monthly faculty salary. |
| `pct_fulltime_faculty` | DECIMAL(5,4) | `PFTFAC` | Share of instruction staff who are full-time, 0–1. |
| `completion_rate_4yr` | DECIMAL(5,4) | `C150_4` | Completion within 150% of normal time (4-year), 0–1. |
| `retention_rate_ft` | DECIMAL(5,4) | `RET_FT4` | Full-time first-year retention, 0–1. |
| `median_debt` | DECIMAL(9,2) | `DEBT_MD` (fallback `GRAD_DEBT_MD`) | Median debt of graduates (USD). |
| `median_earnings_10yr` | DECIMAL(9,2) | `MD_EARN_WNE_P10` (fallback `EARN_MD_10YR`) | Median earnings 10 years after entry (USD). |

## `fields_of_study`

Natural key: (`unit_id`, `cip_code`, `credential_level`); `unit_id` is a
foreign key to `institutions.unit_id`.

| Column | MySQL type | Source column(s) | Description |
|---|---|---|---|
| `unit_id` | INT, PK/FK | `UNITID` | IPEDS UNITID of the offering institution. |
| `cip_code` | VARCHAR(10), PK | `CIPCODE` | CIP code, e.g. `11.0101`. |
| `credential_level` | TINYINT, PK | `CREDENTIAL_LEVEL` | 1 = Certificate, 2 = Associate, 3 = Bachelor's, 4 = Post-baccalaureate certificate, 5 = Master's, 6 = Doctoral, 7 = First professional. |
| `cip_desc` | VARCHAR(255) | `CIPDESC` | Field-of-study description. |
| `median_debt` | DECIMAL(9,2) | `DEBT_MEDIAN` (fallback `DEBT_MD`) | Median debt of program completers (USD). |
| `median_earnings_10yr` | DECIMAL(9,2) | `EARN_MEDIAN_10YR` (fallback `MD_EARN_WNE_P10`) | Median earnings 10 years after graduation (USD). |

## Integrity expectations

- `institutions.unit_id` is unique and non-null (enforced in Python on load
  and by the primary key in MySQL).
- `fields_of_study` composite key is unique and non-null (same enforcement).
- Every `fields_of_study.unit_id` exists in `institutions` (foreign key).
- `control` is NULL or one of 1/2/3; `adm_rate` is NULL or in [0, 1]
  (CHECK constraints + `sql/02_integrity_checks.sql`).

If your release's dictionary disagrees with a source-column name above, update
the `_FIELDS` maps in `src/transform.py` — nothing else needs to change.
