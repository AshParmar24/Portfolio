# Payroll Statutory Change: Employer National Insurance (April 2025)

Business systems analysis for PayFlow Global, a fictional cloud payroll platform. The legislation and figures are real; the client base is synthetic.

## What is in this folder
| File | Purpose |
|---|---|
| `PayFlow_Employer_NIC_Change_Pack.xlsx` | Rates, requirements, business rules, user stories, UAT cases with formula-driven expected results, traceability matrix, impact by salary, estimate |
| `PayFlow_NIC_backlog_jira_import.csv` | The backlog in Jira's CSV import format |
| `nic_reference_calculator.py` | Independent calculation used to check every expected result |
| `client_impact_model.csv`, `client_impact_by_size.csv` | Modelled impact on a synthetic base of 1,150 employer clients |

## Highlights
- 15 requirements, 9 user stories with Given / When / Then acceptance criteria, 22 test cases.
- Every legislative change traced to a rule, requirement, story and test. One gap logged for the next release.
- Found a half-penny rounding case where a spreadsheet ROUND gives the wrong statutory answer (£410.03 instead of £410.02).
- 326 of 1,150 modelled clients pay less or the same after the change because of the larger Employment Allowance.

## Sources
HMRC, Rates and thresholds for employers 2024 to 2025 and 2025 to 2026. HMRC National Insurance Manual NIM11002 (rounding).
