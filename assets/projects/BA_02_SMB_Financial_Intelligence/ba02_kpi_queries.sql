-- Harlow & Finch Trade Supplies: KPI and diagnostic queries (SQLite)
-- Financial years run November to October. FY25 = Nov 2024 to Oct 2025, FY26 = Nov 2025 to Oct 2026.
-- Every KPI on the dashboard is produced by one of the queries below, so each number can be traced to its SQL.

-- name: kpi_headline_by_year
-- Headline KPIs for each financial year: revenue, gross profit, gross margin and average discount.
WITH sales AS (
    SELECT CASE WHEN o.order_date < '2025-11-01' THEN 'FY25' ELSE 'FY26' END AS fin_year,
           l.quantity * l.list_price AS list_value,
           l.net_revenue,
           l.cost_of_sales
    FROM fact_order_lines l
    JOIN fact_orders o ON o.order_id = l.order_id
)
SELECT fin_year,
       ROUND(SUM(net_revenue))                                              AS revenue,
       ROUND(SUM(net_revenue) - SUM(cost_of_sales))                         AS gross_profit,
       ROUND(100.0 * (SUM(net_revenue) - SUM(cost_of_sales)) / SUM(net_revenue), 2) AS gross_margin_pct,
       ROUND(100.0 * (1 - SUM(net_revenue) / SUM(list_value)), 2)           AS avg_discount_pct
FROM sales
GROUP BY fin_year;

-- name: sales_cube_monthly
-- Monthly sales by depot, customer segment and product category. This feeds the dashboard filters.
SELECT strftime('%Y-%m', o.order_date)          AS month,
       d.depot_name                             AS depot,
       c.segment,
       p.category,
       ROUND(SUM(l.quantity * l.list_price), 2) AS list_value,
       ROUND(SUM(l.net_revenue), 2)             AS revenue,
       ROUND(SUM(l.cost_of_sales), 2)           AS cost_of_sales
FROM fact_order_lines l
JOIN fact_orders o   ON o.order_id = l.order_id
JOIN dim_customer c  ON c.customer_id = o.customer_id
JOIN dim_depot d     ON d.depot_id = o.depot_id
JOIN dim_product p   ON p.product_id = l.product_id
GROUP BY 1, 2, 3, 4;

-- name: margin_by_category_year
-- Where did margin move? Gross margin by category, FY25 against FY26, with the change in points.
WITH s AS (
    SELECT p.category,
           CASE WHEN o.order_date < '2025-11-01' THEN 'FY25' ELSE 'FY26' END AS fin_year,
           SUM(l.net_revenue) AS revenue,
           SUM(l.net_revenue) - SUM(l.cost_of_sales) AS gross_profit
    FROM fact_order_lines l
    JOIN fact_orders o ON o.order_id = l.order_id
    JOIN dim_product p ON p.product_id = l.product_id
    GROUP BY 1, 2
)
SELECT category,
       ROUND(SUM(CASE WHEN fin_year = 'FY25' THEN revenue END))                       AS revenue_fy25,
       ROUND(SUM(CASE WHEN fin_year = 'FY26' THEN revenue END))                       AS revenue_fy26,
       ROUND(100.0 * SUM(CASE WHEN fin_year = 'FY25' THEN gross_profit END)
                   / SUM(CASE WHEN fin_year = 'FY25' THEN revenue END), 2)            AS margin_pct_fy25,
       ROUND(100.0 * SUM(CASE WHEN fin_year = 'FY26' THEN gross_profit END)
                   / SUM(CASE WHEN fin_year = 'FY26' THEN revenue END), 2)            AS margin_pct_fy26,
       ROUND(100.0 * SUM(CASE WHEN fin_year = 'FY26' THEN gross_profit END)
                   / SUM(CASE WHEN fin_year = 'FY26' THEN revenue END)
           - 100.0 * SUM(CASE WHEN fin_year = 'FY25' THEN gross_profit END)
                   / SUM(CASE WHEN fin_year = 'FY25' THEN revenue END), 2)            AS change_pts
FROM s
GROUP BY category
ORDER BY change_pts;

-- name: timber_cost_vs_price
-- Timber: average unit cost and average list price per month, indexed to November 2024 = 100.
-- A cost line that climbs while the price line stays flat is a pricing gap, not a sales problem.
WITH m AS (
    SELECT strftime('%Y-%m', o.order_date) AS month,
           SUM(l.quantity * l.unit_cost)  / SUM(l.quantity * p.base_unit_cost) AS cost_ratio,
           SUM(l.quantity * l.list_price) / SUM(l.quantity * p.list_price)     AS price_ratio
    FROM fact_order_lines l
    JOIN fact_orders o ON o.order_id = l.order_id
    JOIN dim_product p ON p.product_id = l.product_id
    WHERE p.category = 'Timber & Sheet'
    GROUP BY 1
)
SELECT month,
       ROUND(100.0 * cost_ratio, 1)  AS unit_cost_index,
       ROUND(100.0 * price_ratio, 1) AS list_price_index
FROM m
ORDER BY month;

-- name: discount_by_rep_year
-- Average discount given by each sales rep on credit accounts, FY25 against FY26, ranked by the increase.
WITH s AS (
    SELECT r.rep_name, d.depot_name AS depot,
           CASE WHEN o.order_date < '2025-11-01' THEN 'FY25' ELSE 'FY26' END AS fin_year,
           SUM(l.quantity * l.list_price) AS list_value,
           SUM(l.net_revenue)             AS revenue
    FROM fact_order_lines l
    JOIN fact_orders o  ON o.order_id = l.order_id
    JOIN dim_customer c ON c.customer_id = o.customer_id
    JOIN dim_rep r      ON r.rep_id = o.rep_id
    JOIN dim_depot d    ON d.depot_id = r.depot_id
    WHERE c.segment <> 'Cash & Retail'
    GROUP BY 1, 2, 3
)
SELECT rep_name, depot,
       ROUND(100.0 * (1 - SUM(CASE WHEN fin_year = 'FY25' THEN revenue END)
                        / SUM(CASE WHEN fin_year = 'FY25' THEN list_value END)), 2) AS discount_pct_fy25,
       ROUND(100.0 * (1 - SUM(CASE WHEN fin_year = 'FY26' THEN revenue END)
                        / SUM(CASE WHEN fin_year = 'FY26' THEN list_value END)), 2) AS discount_pct_fy26,
       ROUND(SUM(CASE WHEN fin_year = 'FY26' THEN list_value END))                  AS list_value_fy26
FROM s
GROUP BY rep_name, depot
ORDER BY discount_pct_fy26 - discount_pct_fy25 DESC;

-- name: discount_trend_flagged_reps
-- Monthly discount for the two flagged reps against everyone else (credit accounts only).
SELECT strftime('%Y-%m', o.order_date) AS month,
       CASE WHEN r.rep_name IN ('E. Purcell', 'F. Sandhu') THEN 'Purcell and Sandhu' ELSE 'All other reps' END AS rep_group,
       ROUND(100.0 * (1 - SUM(l.net_revenue) / SUM(l.quantity * l.list_price)), 2) AS discount_pct
FROM fact_order_lines l
JOIN fact_orders o  ON o.order_id = l.order_id
JOIN dim_customer c ON c.customer_id = o.customer_id
JOIN dim_rep r      ON r.rep_id = o.rep_id
WHERE c.segment <> 'Cash & Retail'
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: days_to_pay_monthly
-- Cash collection: value-weighted average days from invoice to payment, by invoice month and segment.
-- Credit customers only. Unpaid invoices are excluded, so the latest two months understate the true figure.
SELECT strftime('%Y-%m', i.invoice_date) AS month,
       c.segment,
       ROUND(SUM(i.amount * (julianday(i.paid_date) - julianday(i.invoice_date))) / SUM(i.amount), 1) AS avg_days_to_pay,
       ROUND(SUM(i.amount)) AS invoiced_value
FROM fact_invoices i
JOIN fact_orders o  ON o.order_id = i.order_id
JOIN dim_customer c ON c.customer_id = o.customer_id
WHERE c.segment <> 'Cash & Retail'
  AND i.paid_date IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: aged_debt_snapshot
-- Aged debt at the reporting date (31 October 2026): what is owed, and how overdue it is.
WITH open_items AS (
    SELECT c.segment, i.amount,
           julianday('2026-10-31') - julianday(i.due_date) AS days_overdue
    FROM fact_invoices i
    JOIN fact_orders o  ON o.order_id = i.order_id
    JOIN dim_customer c ON c.customer_id = o.customer_id
    WHERE i.paid_date IS NULL
)
SELECT segment,
       ROUND(SUM(CASE WHEN days_overdue <= 0 THEN amount ELSE 0 END))               AS not_yet_due,
       ROUND(SUM(CASE WHEN days_overdue BETWEEN 1 AND 30 THEN amount ELSE 0 END))   AS overdue_1_30,
       ROUND(SUM(CASE WHEN days_overdue > 30 THEN amount ELSE 0 END))               AS overdue_over_30,
       ROUND(SUM(amount))                                                           AS total_owed
FROM open_items
GROUP BY segment;

-- name: late_payers_top_accounts
-- Which accounts drive the slowdown? Largest trade accounts, days to pay FY25 against FY26.
WITH p AS (
    SELECT o.customer_id,
           CASE WHEN i.invoice_date < '2025-11-01' THEN 'FY25' ELSE 'FY26' END AS fin_year,
           SUM(i.amount) AS invoiced,
           SUM(i.amount * (julianday(i.paid_date) - julianday(i.invoice_date))) / SUM(i.amount) AS days_to_pay
    FROM fact_invoices i
    JOIN fact_orders o  ON o.order_id = i.order_id
    JOIN dim_customer c ON c.customer_id = o.customer_id
    WHERE c.segment = 'Trade Account' AND i.paid_date IS NOT NULL AND i.invoice_date < '2026-09-01'
    GROUP BY 1, 2
)
SELECT customer_id,
       ROUND(SUM(invoiced))                                             AS invoiced_two_years,
       ROUND(MAX(CASE WHEN fin_year = 'FY25' THEN days_to_pay END), 1)  AS days_to_pay_fy25,
       ROUND(MAX(CASE WHEN fin_year = 'FY26' THEN days_to_pay END), 1)  AS days_to_pay_fy26
FROM p
GROUP BY customer_id
ORDER BY invoiced_two_years DESC
LIMIT 15;

-- name: otif_monthly_by_depot
-- Operations: on time in full (OTIF) by depot and month.
-- A delivery counts only if it was dispatched on or before the promised date and was complete.
SELECT strftime('%Y-%m', o.order_date) AS month,
       d.depot_name AS depot,
       COUNT(*) AS deliveries,
       SUM(CASE WHEN f.dispatched_date <= f.promised_date AND f.complete_flag = 1 THEN 1 ELSE 0 END) AS on_time_in_full,
       ROUND(100.0 * SUM(CASE WHEN f.dispatched_date <= f.promised_date AND f.complete_flag = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS otif_pct
FROM fact_deliveries f
JOIN fact_orders o ON o.order_id = f.order_id
JOIN dim_depot d   ON d.depot_id = f.depot_id
GROUP BY 1, 2
ORDER BY 1, 2;
