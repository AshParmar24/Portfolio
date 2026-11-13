-- Soar Valley Homes: repairs performance queries (SQLite)
-- Period: May 2025 to October 2026. Reporting date: 31 October 2026.
-- A job meets its target when it is completed within target_days of being reported
-- (Emergency 1 day, Urgent 7 days, Routine 28 days). Open jobs already past target count as missed.

-- name: sla_monthly_by_priority
-- Share of jobs completed within target, by month reported and priority.
SELECT strftime('%Y-%m', reported_date) AS month,
       priority,
       COUNT(*) AS jobs,
       SUM(CASE WHEN completed_date IS NOT NULL
                 AND julianday(completed_date) - julianday(reported_date) <= target_days THEN 1 ELSE 0 END) AS within_target,
       ROUND(100.0 * SUM(CASE WHEN completed_date IS NOT NULL
                 AND julianday(completed_date) - julianday(reported_date) <= target_days THEN 1 ELSE 0 END) / COUNT(*), 1) AS within_target_pct
FROM fact_repair_jobs
WHERE julianday('2026-10-31') - julianday(reported_date) >= target_days   -- only jobs old enough to be judged
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: sla_monthly_by_contractor
-- The same measure by contractor, to see whether the fall is general or concentrated.
SELECT strftime('%Y-%m', reported_date) AS month,
       contractor,
       COUNT(*) AS jobs,
       SUM(CASE WHEN completed_date IS NOT NULL
                 AND julianday(completed_date) - julianday(reported_date) <= target_days THEN 1 ELSE 0 END) AS within_target,
       ROUND(100.0 * SUM(CASE WHEN completed_date IS NOT NULL
                 AND julianday(completed_date) - julianday(reported_date) <= target_days THEN 1 ELSE 0 END) / COUNT(*), 1) AS within_target_pct
FROM fact_repair_jobs
WHERE julianday('2026-10-31') - julianday(reported_date) >= target_days
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: contractor_scorecard
-- Contractor scorecard, first eight months against the latest ten (January 2026 onwards).
SELECT contractor,
       CASE WHEN reported_date < '2026-01-01' THEN '1. May to Dec 2025' ELSE '2. Jan to Oct 2026' END AS period,
       COUNT(*) AS jobs,
       ROUND(100.0 * SUM(CASE WHEN completed_date IS NOT NULL
                 AND julianday(completed_date) - julianday(reported_date) <= target_days THEN 1 ELSE 0 END) / COUNT(*), 1) AS within_target_pct,
       ROUND(100.0 * AVG(first_time_fix), 1)                                        AS first_time_fix_pct,
       ROUND(AVG(julianday(completed_date) - julianday(reported_date)), 1)          AS avg_days_to_complete,
       ROUND(AVG(satisfaction_score), 2)                                            AS avg_satisfaction,
       ROUND(AVG(job_cost), 2)                                                      AS avg_job_cost
FROM fact_repair_jobs
WHERE julianday('2026-10-31') - julianday(reported_date) >= target_days
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: no_access_by_channel
-- No-access visits by how the appointment was booked. Portal bookings send a text reminder.
SELECT booking_channel,
       COUNT(*)                                                         AS jobs,
       SUM(no_access_visits)                                            AS no_access_visits,
       ROUND(100.0 * SUM(CASE WHEN no_access_visits > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS jobs_with_no_access_pct,
       ROUND(1.0 * SUM(no_access_visits) / COUNT(*), 3)                 AS no_access_visits_per_job
FROM fact_repair_jobs
WHERE priority <> 'Emergency'
GROUP BY booking_channel
ORDER BY jobs DESC;

-- name: first_time_fix_by_trade
-- First-time fix, repeat reports and cost by trade (completed jobs).
SELECT trade,
       COUNT(*)                                        AS completed_jobs,
       ROUND(100.0 * AVG(first_time_fix), 1)           AS first_time_fix_pct,
       ROUND(100.0 * AVG(repeat_within_90_days), 1)    AS repeat_within_90_days_pct,
       ROUND(AVG(job_cost), 2)                         AS avg_job_cost,
       ROUND(SUM(job_cost))                            AS total_cost
FROM fact_repair_jobs
WHERE status = 'Completed'
GROUP BY trade
ORDER BY first_time_fix_pct;

-- name: damp_mould_monthly
-- Damp and mould: reports per month and the share visited within 14 calendar days.
-- 14 calendar days is used as a simple stand-in for the 10 working day investigation duty under Awaab's Law.
SELECT strftime('%Y-%m', reported_date) AS month,
       COUNT(*) AS reports,
       ROUND(100.0 * SUM(CASE WHEN first_visit_date IS NOT NULL
                 AND julianday(first_visit_date) - julianday(reported_date) <= 14 THEN 1 ELSE 0 END) / COUNT(*), 1) AS visited_within_14_days_pct
FROM fact_repair_jobs
WHERE trade = 'Damp & Mould'
  AND julianday('2026-10-31') - julianday(reported_date) >= 14
GROUP BY 1
ORDER BY 1;

-- name: open_jobs_month_end
-- Work in progress: jobs open at each month end (reported on or before, not completed by, that date).
WITH RECURSIVE month_ends(d) AS (
    SELECT date('2025-05-31')
    UNION ALL
    SELECT date(d, 'start of month', '+2 months', '-1 day') FROM month_ends WHERE d < '2026-10-31'
)
SELECT m.d AS month_end,
       COUNT(*) AS open_jobs,
       SUM(CASE WHEN julianday(m.d) - julianday(j.reported_date) > j.target_days THEN 1 ELSE 0 END) AS open_past_target
FROM month_ends m
JOIN fact_repair_jobs j
  ON j.reported_date <= m.d
 AND (j.completed_date IS NULL OR j.completed_date > m.d)
GROUP BY m.d
ORDER BY m.d;

-- name: satisfaction_by_outcome
-- Tenant satisfaction (1 to 5) by whether the job met target and was fixed first time.
SELECT CASE WHEN julianday(completed_date) - julianday(reported_date) <= target_days THEN 'Within target' ELSE 'Missed target' END AS target_outcome,
       CASE WHEN first_time_fix = 1 THEN 'Fixed first time' ELSE 'Needed a return visit' END AS fix_outcome,
       COUNT(satisfaction_score)          AS responses,
       ROUND(AVG(satisfaction_score), 2)  AS avg_satisfaction
FROM fact_repair_jobs
WHERE satisfaction_score IS NOT NULL
GROUP BY 1, 2
ORDER BY avg_satisfaction DESC;

-- name: avoidable_cost_last_12_months
-- Avoidable activity in the last 12 months (November 2025 to October 2026), used in the business case.
SELECT COUNT(*)                                                                   AS jobs_reported,
       SUM(no_access_visits)                                                      AS no_access_visits,
       SUM(CASE WHEN booking_channel = 'Phone' THEN 1 ELSE 0 END)                 AS phone_booked_jobs,
       SUM(CASE WHEN status = 'Completed' THEN completed_visits - 1 ELSE 0 END)   AS return_visits,
       SUM(CASE WHEN repeat_within_90_days = 1 THEN 1 ELSE 0 END)                 AS repeat_reports,
       ROUND(SUM(job_cost))                                                       AS total_job_cost,
       ROUND(AVG(job_cost / completed_visits), 2)                                 AS avg_cost_per_visit
FROM fact_repair_jobs
WHERE reported_date >= '2025-11-01';

-- name: sla_cube
-- Monthly jobs and jobs within target by contractor, priority and area. This feeds the dashboard filters.
SELECT strftime('%Y-%m', reported_date) AS month, contractor, priority, area,
       COUNT(*) AS jobs,
       SUM(CASE WHEN completed_date IS NOT NULL
                 AND julianday(completed_date) - julianday(reported_date) <= target_days THEN 1 ELSE 0 END) AS within_target,
       SUM(COALESCE(first_time_fix, 0)) AS fixed_first_time,
       SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_jobs,
       SUM(no_access_visits) AS no_access_visits
FROM fact_repair_jobs
WHERE julianday('2026-10-31') - julianday(reported_date) >= target_days
GROUP BY 1, 2, 3, 4;
