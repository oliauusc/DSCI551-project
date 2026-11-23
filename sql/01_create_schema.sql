-- 01_create_schema.sql
-- College Scorecard schema (MySQL 8.0+; CHECK constraints need 8.0.16+).
-- Run first — sql/02–04 assume this schema exists.
--   mysql -u <user> -p < sql/01_create_schema.sql

CREATE DATABASE IF NOT EXISTS college_scorecard
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;  -- MySQL 5.7 fallback: utf8mb4_unicode_ci

USE college_scorecard;

CREATE TABLE institutions (
  unit_id              INT              NOT NULL COMMENT 'IPEDS UNITID (natural key)',
  inst_name            VARCHAR(255)     NOT NULL,
  city                 VARCHAR(120),
  state                CHAR(2)          COMMENT '2-letter USPS code',
  zip_code             VARCHAR(10),
  accreditation        VARCHAR(255),
  inst_url             VARCHAR(255),
  net_price_url        VARCHAR(255),
  control              TINYINT          COMMENT '1=Public, 2=Private nonprofit, 3=Private for-profit',
  locale               SMALLINT         COMMENT 'Scorecard locale code (11=City large ... 43=Rural remote)',
  carnegie_basic       SMALLINT         COMMENT 'CC_BASIC Carnegie classification code',
  adm_rate             DECIMAL(5,4)     COMMENT 'Admission rate, 0..1 (PrivacySuppressed -> NULL)',
  sat_avg              SMALLINT         COMMENT 'Average SAT equivalent (suppressed -> NULL)',
  undergrad_size       INT              COMMENT 'UGDS: undergraduate enrollment',
  tuition_in_state     MEDIUMINT UNSIGNED,
  tuition_out_state    MEDIUMINT UNSIGNED,
  avg_faculty_salary   MEDIUMINT UNSIGNED COMMENT 'Monthly average faculty salary',
  pct_fulltime_faculty DECIMAL(5,4),
  completion_rate_4yr  DECIMAL(5,4)     COMMENT 'C150_4 completion rate within 150% of normal time',
  retention_rate_ft    DECIMAL(5,4)     COMMENT 'RET_FT4 full-time first-year retention',
  median_debt          DECIMAL(9,2)     COMMENT 'Median debt of graduates (USD)',
  median_earnings_10yr DECIMAL(9,2)     COMMENT 'Median earnings 10 years after entry (USD)',
  PRIMARY KEY (unit_id),
  KEY idx_inst_state_control (state, control),
  KEY idx_inst_adm_rate (adm_rate),
  CONSTRAINT chk_inst_control  CHECK (control IS NULL OR control IN (1, 2, 3)),
  CONSTRAINT chk_inst_adm_rate CHECK (adm_rate IS NULL OR adm_rate BETWEEN 0 AND 1)
) ENGINE=InnoDB;

CREATE TABLE fields_of_study (
  unit_id              INT          NOT NULL,
  cip_code             VARCHAR(10)  NOT NULL COMMENT 'CIP code, e.g. 11.0101',
  credential_level     TINYINT      NOT NULL COMMENT '1=Certificate, 2=Associate, 3=Bachelor''s, 4=Post-bacc certificate, 5=Master''s, 6=Doctoral, 7=First professional',
  cip_desc             VARCHAR(255) COMMENT 'Field-of-study description',
  median_debt          DECIMAL(9,2) COMMENT 'Median debt of program completers (USD)',
  median_earnings_10yr DECIMAL(9,2) COMMENT 'Median earnings 10 years after graduation (USD)',
  PRIMARY KEY (unit_id, cip_code, credential_level),
  KEY idx_fos_cip (cip_code, credential_level),
  CONSTRAINT fk_fos_institution FOREIGN KEY (unit_id)
    REFERENCES institutions (unit_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Load order: institutions first, then fields_of_study (FK dependency).
