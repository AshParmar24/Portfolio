# Housing Repairs Service Review

Service performance analysis for Soar Valley Homes, a fictional housing association with about 6,200 homes. The dataset is synthetic and reproducible.

## Business problem
Repairs completed within target were falling, complaints were rising and damp and mould reports had doubled after Awaab's Law took effect in October 2025.

## What is in this folder
| File | Purpose |
|---|---|
| `ba04_repairs_queries.sql` | Ten named SQL queries: targets, contractors, no access, first-time fix, damp and mould, work in progress |
| `ba04_analysis.py` | Runs the queries and sizes each finding |
| `ba04_generate_data.py` | Seeded generator for the synthetic dataset |
| `data/` | Repairs jobs and properties as CSV, plus the SQLite database |
| `outputs/` | One CSV per query |
| `Tableau_Public_build_guide.md` | Steps to rebuild the dashboard in Tableau Public |

## Headline findings
- Completed within target fell from 83 to 74 percent. One contractor accounts for the fall (84 to 63 percent); the others held at about 82 percent.
- Phone bookings average 0.24 no-access visits per job against 0.09 for portal bookings with a text reminder.
- Damp and mould reports doubled; first-time fix is 49 percent.
- Jobs open and past target rose from 68 to 124 in a year.

## How to run
```
python ba04_generate_data.py .
python ba04_analysis.py .
```
Requires Python 3 with pandas and numpy.
