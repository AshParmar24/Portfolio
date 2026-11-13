# Rebuilding the dashboard in Tableau Public

Tableau Public is free and runs on Mac and Windows. These steps recreate the main views from the CSV files in this folder.

## 1. Connect the data
1. Open Tableau Public and choose **Text file**. Select `outputs/sales_cube_monthly.csv`.
2. On the Data Source page, change the `month` field type to **Date** (it is stored as YYYY-MM).
3. Add two more data sources the same way: `outputs/days_to_pay_monthly.csv` and `outputs/otif_monthly_by_depot.csv`.

## 2. Create the calculated fields (sales data source)
| Name | Formula |
|---|---|
| Gross Profit | `SUM([revenue]) - SUM([cost_of_sales])` |
| Gross Margin % | `(SUM([revenue]) - SUM([cost_of_sales])) / SUM([revenue])` |
| Average Discount % | `1 - SUM([revenue]) / SUM([list_value])` |
| Financial Year | `IF [month] < #2025-11-01# THEN "FY25" ELSE "FY26" END` |

Format the two percentage fields as Percentage with one decimal place.

## 3. Build the sheets
| Sheet | Columns | Rows | Marks |
|---|---|---|---|
| Monthly revenue | `MONTH(month)` (continuous) | `SUM(revenue)` | Bar |
| Margin trend | `MONTH(month)` (continuous) | `Gross Margin %` | Line |
| Margin by category | `Gross Margin %` | `category` | Bar, with `Financial Year` on Colour |
| Days to pay | `MONTH(month)` | `AVG(avg_days_to_pay)` | Line, `segment` on Colour |
| OTIF by depot | `MONTH(month)` | `AVG(otif_pct)` | Line, `depot` on Colour |
| KPI tiles | one sheet per KPI with the measure on Text | | Text |

## 4. Assemble the dashboard
1. New Dashboard, size **Automatic**.
2. Place the KPI tiles in a row at the top, the two trend charts beneath, then category, days to pay and OTIF.
3. Add `depot`, `segment` and `Financial Year` as filters and set each to **Apply to worksheets > All using this data source**.
4. Add a title and a short text box stating that the data is synthetic.

## 5. Publish
**File > Save to Tableau Public**. Copy the share link and add it to the project page.
