-- 04_index_experiments.sql
-- A/B comparison of index designs using EXPLAIN and EXPLAIN ANALYZE
-- (EXPLAIN ANALYZE requires MySQL 8.0.18+; run on the loaded database).
--
-- For each experiment:
--   1. drop the index under test and capture the baseline plan + timing,
--   2. re-create the index and capture the same query again,
--   3. record whether the plan changed (scan -> ref/range) and the time delta.
-- Paste the before/after plans into results/index_experiments.md (gitignored)
-- and summarize the takeaway in the notebook's interpretation section.

USE college_scorecard;

-- ---------------------------------------------------------------------------
-- Experiment 1: state + ownership filter (drives the Streamlit sidebar).
-- Hypothesis: the composite index (state, control) serves both equality
-- predicates with a single lookup and beats separate single-column indexes.
-- ---------------------------------------------------------------------------
ALTER TABLE institutions DROP INDEX idx_inst_state_control;

EXPLAIN
SELECT unit_id, inst_name, city, state, adm_rate,
       tuition_in_state, tuition_out_state
FROM institutions
WHERE state = 'CA' AND control = 1;

EXPLAIN ANALYZE
SELECT unit_id, inst_name, city, state, adm_rate,
       tuition_in_state, tuition_out_state
FROM institutions
WHERE state = 'CA' AND control = 1;

ALTER TABLE institutions ADD INDEX idx_inst_state_control (state, control);

EXPLAIN ANALYZE
SELECT unit_id, inst_name, city, state, adm_rate,
       tuition_in_state, tuition_out_state
FROM institutions
WHERE state = 'CA' AND control = 1;

-- ---------------------------------------------------------------------------
-- Experiment 2: admission-rate range filter.
-- Hypothesis: a range predicate on adm_rate benefits less than the equality
-- filters in Experiment 1 — measure whether the range still narrows enough
-- rows for the index to pay off on this data.
-- ---------------------------------------------------------------------------
ALTER TABLE institutions DROP INDEX idx_inst_adm_rate;

EXPLAIN
SELECT unit_id, inst_name, state, control, adm_rate, undergrad_size
FROM institutions
WHERE adm_rate BETWEEN 0.25 AND 0.45;

EXPLAIN ANALYZE
SELECT unit_id, inst_name, state, control, adm_rate, undergrad_size
FROM institutions
WHERE adm_rate BETWEEN 0.25 AND 0.45;

ALTER TABLE institutions ADD INDEX idx_inst_adm_rate (adm_rate);

EXPLAIN ANALYZE
SELECT unit_id, inst_name, state, control, adm_rate, undergrad_size
FROM institutions
WHERE adm_rate BETWEEN 0.25 AND 0.45;

-- ---------------------------------------------------------------------------
-- Experiment 3: field-of-study lookup joined back to institutions.
-- Substitute a CIP code that exists in the loaded data (check cip_code values).
-- Hypothesis: idx_fos_cip turns the outer scan into a ref lookup; adding the
-- earnings column makes the index covering and removes the row lookups.
-- ---------------------------------------------------------------------------
ALTER TABLE fields_of_study DROP INDEX idx_fos_cip;

EXPLAIN
SELECT i.inst_name, i.state, f.cip_desc, f.median_earnings_10yr
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.cip_code = '11.0101'
ORDER BY f.median_earnings_10yr DESC;

EXPLAIN ANALYZE
SELECT i.inst_name, i.state, f.cip_desc, f.median_earnings_10yr
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.cip_code = '11.0101'
ORDER BY f.median_earnings_10yr DESC;

ALTER TABLE fields_of_study ADD INDEX idx_fos_cip (cip_code, credential_level);

EXPLAIN ANALYZE
SELECT i.inst_name, i.state, f.cip_desc, f.median_earnings_10yr
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.cip_code = '11.0101'
ORDER BY f.median_earnings_10yr DESC;

-- Stretch: does a covering index remove the row lookups entirely?
ALTER TABLE fields_of_study
  ADD INDEX idx_fos_covering (cip_code, unit_id, median_earnings_10yr);

EXPLAIN ANALYZE
SELECT i.inst_name, i.state, f.cip_desc, f.median_earnings_10yr
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.cip_code = '11.0101'
ORDER BY f.median_earnings_10yr DESC;

ALTER TABLE fields_of_study DROP INDEX idx_fos_covering;
