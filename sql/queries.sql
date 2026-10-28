-- Table: encounters (the cleaned dataset, one row per patient)

-- name: overall_kpis
SELECT COUNT(*) AS patients,
       ROUND(100.0 * AVG(readmitted_30d), 2) AS readmit_rate_pct,
       ROUND(AVG(time_in_hospital), 2) AS avg_length_of_stay_days
FROM encounters;

-- name: by_age_group
SELECT age_group,
       COUNT(*) AS patients,
       ROUND(100.0 * AVG(readmitted_30d), 2) AS readmit_rate_pct
FROM encounters
GROUP BY age_group
ORDER BY readmit_rate_pct DESC;

-- name: by_a1c_status
SELECT a1c_status,
       COUNT(*) AS patients,
       ROUND(100.0 * AVG(readmitted_30d), 2) AS readmit_rate_pct
FROM encounters
GROUP BY a1c_status
ORDER BY readmit_rate_pct DESC;

-- name: by_length_of_stay_bucket
SELECT CASE WHEN time_in_hospital <= 3 THEN '1-3 days'
            WHEN time_in_hospital <= 7 THEN '4-7 days'
            ELSE '8-14 days' END AS los_bucket,
       COUNT(*) AS patients,
       ROUND(100.0 * AVG(readmitted_30d), 2) AS readmit_rate_pct
FROM encounters
GROUP BY los_bucket
ORDER BY MIN(time_in_hospital);

-- name: by_prior_inpatient_visits
SELECT CASE WHEN number_inpatient = 0 THEN '0'
            WHEN number_inpatient = 1 THEN '1'
            ELSE '2+' END AS prior_inpatient_visits,
       COUNT(*) AS patients,
       ROUND(100.0 * AVG(readmitted_30d), 2) AS readmit_rate_pct
FROM encounters
GROUP BY prior_inpatient_visits
ORDER BY prior_inpatient_visits;

-- name: top_specialties_min_100_patients
SELECT medical_specialty,
       COUNT(*) AS patients,
       ROUND(100.0 * AVG(readmitted_30d), 2) AS readmit_rate_pct
FROM encounters
WHERE medical_specialty <> 'Unknown'
GROUP BY medical_specialty
HAVING COUNT(*) >= 100
ORDER BY readmit_rate_pct DESC
LIMIT 10;

-- name: diagnosis_risk_ranking
WITH rates AS (
    SELECT diag_group,
           COUNT(*) AS patients,
           AVG(readmitted_30d) AS rate
    FROM encounters
    GROUP BY diag_group
)
SELECT diag_group,
       patients,
       ROUND(100.0 * rate, 2) AS readmit_rate_pct,
       RANK() OVER (ORDER BY rate DESC) AS risk_rank
FROM rates
ORDER BY risk_rank;