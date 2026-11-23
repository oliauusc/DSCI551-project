-- 03_workload_queries.sql
-- The analytical workload. Each query states the business question it answers.
-- Run individual statements or the whole file:
--   mysql -u <user> -p college_scorecard < sql/03_workload_queries.sql
-- The Python mirrors of Q1–Q4 live in src/query_mysql.py (used by app + tests).

USE college_scorecard;

-- Q1: Explorer filter — which schools match a state / ownership / admission
--     profile? (Drives the Streamlit sidebar.)
SELECT unit_id, inst_name, city, state, control, adm_rate, sat_avg,
       tuition_in_state, tuition_out_state, completion_rate_4yr,
       median_debt, median_earnings_10yr
FROM institutions
WHERE state IN ('CA', 'WA') AND control = 1 AND adm_rate BETWEEN 0.30 AND 0.90
ORDER BY inst_name
LIMIT 200;

-- Q2: Which fields of study lead to the highest median earnings 10 years out?
SELECT i.inst_name, i.state, f.cip_desc, f.credential_level,
       f.median_debt, f.median_earnings_10yr
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.median_earnings_10yr IS NOT NULL
ORDER BY f.median_earnings_10yr DESC
LIMIT 25;

-- Q3: How does published tuition vary across states?
SELECT state,
       COUNT(*)                        AS institutions,
       AVG(tuition_in_state)           AS avg_tuition_in_state,
       AVG(tuition_out_state)          AS avg_tuition_out_of_state
FROM institutions
WHERE state IS NOT NULL
GROUP BY state
ORDER BY avg_tuition_in_state DESC;

-- Q4: How do completion, debt, and earnings differ by ownership type?
SELECT CASE control WHEN 1 THEN 'Public'
                    WHEN 2 THEN 'Private nonprofit'
                    WHEN 3 THEN 'Private for-profit'
                    ELSE 'Unknown' END AS control_label,
       COUNT(*)                        AS institutions,
       AVG(completion_rate_4yr)        AS avg_completion_rate,
       AVG(median_debt)                AS avg_median_debt,
       AVG(median_earnings_10yr)       AS avg_median_earnings_10yr
FROM institutions
WHERE control IN (1, 2, 3)
GROUP BY control;

-- Q5: Debt pressure — where does median debt consume the largest share of a
--     decade of median earnings? (Only rows with both measures.)
SELECT i.inst_name, i.state, f.cip_desc,
       f.median_debt,
       f.median_earnings_10yr,
       ROUND(f.median_debt / NULLIF(f.median_earnings_10yr, 0), 3) AS debt_to_decade_earnings
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.median_debt IS NOT NULL AND f.median_earnings_10yr IS NOT NULL
ORDER BY debt_to_decade_earnings DESC
LIMIT 25;

-- Q6: Program breadth — how widely is a field offered across states?
--     Substitute a keyword to match a field of interest.
SELECT i.state,
       COUNT(DISTINCT i.unit_id) AS institutions_offering_field
FROM fields_of_study AS f
JOIN institutions AS i ON i.unit_id = f.unit_id
WHERE f.cip_desc LIKE '%Computer Science%'
GROUP BY i.state
ORDER BY institutions_offering_field DESC;

-- Q7: Selective large institutions — enrollment above 10,000 admitting fewer
--     than half of applicants, ranked by entering academic profile.
SELECT inst_name, city, state, control, adm_rate, sat_avg, undergrad_size,
       completion_rate_4yr, median_earnings_10yr
FROM institutions
WHERE undergrad_size > 10000 AND adm_rate IS NOT NULL AND adm_rate <= 0.50
ORDER BY sat_avg DESC
LIMIT 25;

-- Q8: Coverage — institutions and field-of-study rows per state (data
--     completeness view used when interpreting other queries).
SELECT i.state,
       COUNT(DISTINCT i.unit_id)  AS institutions,
       COUNT(f.unit_id)           AS field_of_study_rows
FROM institutions AS i
LEFT JOIN fields_of_study AS f ON f.unit_id = i.unit_id
GROUP BY i.state
ORDER BY institutions DESC;
