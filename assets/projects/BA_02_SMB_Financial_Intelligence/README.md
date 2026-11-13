# SMB Operational and Financial Intelligence

A Datavra case study for Harlow & Finch Trade Supplies, a fictional three-depot trade wholesaler. The dataset is synthetic and reproducible.

## Business problem
Sales were rising and profit was falling. The owners had no view of margin by product, discount by rep, how quickly customers paid, or delivery performance by depot.

## What is in this folder
| File | Purpose |
|---|---|
| `KPI_Framework_and_Data_Dictionary.xlsx` | KPI definitions with owners and targets, full data dictionary, findings summary |
| `ba02_kpi_queries.sql` | Ten named SQL queries behind every dashboard number |
| `ba02_analysis.py` | Runs the queries, builds the gross profit bridge, sizes each finding |
| `ba02_generate_data.py` | Seeded generator for the synthetic dataset |
| `data/` | CSV tables and the SQLite database |
| `outputs/` | One CSV per query, plus the gross profit bridge |
| `Tableau_Public_build_guide.md` | Steps to rebuild the dashboard in Tableau Public |

## Headline findings
- Gross margin fell from 27.1 to 24.4 percent while revenue grew 1.9 percent.
- Timber supplier costs rose 13 percent in February 2026 with no price change: £168,129 of gross profit in FY26.
- Two reps at one depot increased discounts on credit accounts: £78,752.
- Trade accounts now take 51 days to pay against 39, tying up about £223,702.
- Derby on time in full fell from 90 to 78 percent from June 2026.

## How to run
```
python ba02_generate_data.py .
python ba02_analysis.py .
```
Requires Python 3 with pandas and numpy.
