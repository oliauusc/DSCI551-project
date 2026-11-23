-- 02_integrity_checks.sql
-- Run after loading data. Every `violations` value should be 0; the coverage
-- queries at the bottom describe how much of the key columns actually loaded.
--   mysql -u <user> -p college_scorecard < sql/02_integrity_checks.sql

USE college_scorecard;

-- ---- Referential & key integrity ------------------------------------------

SELECT 'duplicate institution PKs' AS check_name, COUNT(*) AS violations
FROM (SELECT unit_id FROM institutions GROUP BY unit_id HAVING COUNT(*) > 1) AS d
UNION ALL
SELECT 'orphan field-of-study rows (no matching institution)', COUNT(*)
FROM fields_of_study AS f
LEFT JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE i.unit_id IS NULL
UNION ALL
SELECT 'duplicate field-of-study natural keys', COUNT(*)
FROM (SELECT unit_id, cip_code, credential_level
      FROM fields_of_study
      GROUP BY unit_id, cip_code, credential_level
      HAVING COUNT(*) > 1) AS d
UNION ALL
SELECT 'invalid control values (must be 1/2/3 or NULL)', COUNT(*)
FROM institutions
WHERE control IS NOT NULL AND control NOT IN (1, 2, 3)
UNION ALL
SELECT 'admission rates outside [0, 1]', COUNT(*)
FROM institutions
WHERE adm_rate IS NOT NULL AND (adm_rate < 0 OR adm_rate > 1)
UNION ALL
SELECT 'state codes not 2 characters', COUNT(*)
FROM institutions
WHERE state IS NOT NULL AND CHAR_LENGTH(state) <> 2
UNION ALL
SELECT 'rows missing unit_id or inst_name', COUNT(*)
FROM institutions
WHERE unit_id IS NULL OR inst_name IS NULL OR inst_name = '';

-- ---- Coverage (NULL = suppressed or not reported in the source release) ----

SELECT
  COUNT(*)                          AS institutions_loaded,
  SUM(control IS NULL)              AS control_missing,
  SUM(adm_rate IS NULL)             AS adm_rate_missing,
  SUM(sat_avg IS NULL)              AS sat_avg_missing,
  SUM(completion_rate_4yr IS NULL)  AS completion_missing,
  SUM(median_debt IS NULL)          AS median_debt_missing,
  SUM(median_earnings_10yr IS NULL) AS earnings_missing
FROM institutions;

SELECT
  COUNT(*)                          AS field_of_study_rows,
  SUM(median_debt IS NULL)          AS median_debt_missing,
  SUM(median_earnings_10yr IS NULL) AS earnings_missing
FROM fields_of_study;

-- Rows per state — spot-check against the source release.
SELECT state, COUNT(*) AS institutions
FROM institutions
GROUP BY state
ORDER BY institutions DESC;
