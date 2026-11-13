# Rebuilding the dashboard in Tableau Public

Tableau Public is free and runs on Mac and Windows.

## 1. Connect the data
1. Open Tableau Public, choose **Text file** and select `data/fact_repair_jobs.csv`.
2. Check that `reported_date`, `first_visit_date` and `completed_date` are typed as **Date**.

## 2. Create the calculated fields
| Name | Formula |
|---|---|
| Days To Complete | `DATEDIFF('day', [reported_date], [completed_date])` |
| Old Enough To Judge | `DATEDIFF('day', [reported_date], #2026-10-31#) >= [target_days]` |
| Within Target | `IF NOT ISNULL([completed_date]) AND [Days To Complete] <= [target_days] THEN 1 ELSE 0 END` |
| Within Target % | `SUM([Within Target]) / COUNT([job_id])` |
| First Time Fix % | `AVG([first_time_fix])` |
| No Access Per Job | `SUM([no_access_visits]) / COUNT([job_id])` |
| Visited Within 14 Days | `IF NOT ISNULL([first_visit_date]) AND DATEDIFF('day', [reported_date], [first_visit_date]) <= 14 THEN 1 ELSE 0 END` |

Add **Old Enough To Judge = True** as a data source filter so recent jobs do not drag the within-target figure down.

## 3. Build the sheets
| Sheet | Columns | Rows | Marks |
|---|---|---|---|
| Within target by contractor | `MONTH(reported_date)` (continuous) | `Within Target %` | Line, `contractor` on Colour |
| Within target by priority | `MONTH(reported_date)` (continuous) | `Within Target %` | Line, `priority` on Colour |
| No access by channel | `booking_channel` | `No Access Per Job` | Bar |
| First-time fix by trade | `First Time Fix %` | `trade` (sorted ascending) | Bar |
| Damp and mould reports | `MONTH(reported_date)` | `COUNT(job_id)` | Bar, filtered to trade = Damp & Mould |

## 4. Assemble and publish
1. New Dashboard, size **Automatic**. KPI tiles on top, the two trend lines beneath, then the bars.
2. Add `contractor`, `priority` and `area` filters and apply them to all worksheets using this data source.
3. Add a text box stating that the data is synthetic.
4. **File > Save to Tableau Public**, then add the share link to the project page.
