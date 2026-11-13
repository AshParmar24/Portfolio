"""
Soar Valley Homes: repairs analysis pipeline
--------------------------------------------
Runs every named query in ba04_repairs_queries.sql, sizes the findings and
writes the dashboard data file plus one CSV per query.

Run:  python ba04_analysis.py <project_folder>
"""
import sys, os, json, sqlite3
import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
con = sqlite3.connect(os.path.join(ROOT, "data", "soar_valley_repairs.db"))
res = {}
for block in open(os.path.join(ROOT, "ba04_repairs_queries.sql")).read().split("-- name: ")[1:]:
    name, body = block.split("\n", 1)
    res[name.strip()] = pd.read_sql(body, con)

def pct(df):
    return 100 * df.within_target.sum() / df.jobs.sum()

cube = res["sla_cube"]
early, late = cube[cube.month < "2026-01"], cube[cube.month >= "2026-01"]
K = "Kestrel Property Services"
na = res["no_access_by_channel"].set_index("booking_channel")
portal_rate = na.loc["Online portal", "no_access_visits_per_job"]
year = res["avoidable_cost_last_12_months"].iloc[0]

# No-access visits that would not happen if phone and email bookings had the portal's rate (last 12 months)
last12 = pd.read_sql("""SELECT booking_channel, COUNT(*) jobs, SUM(no_access_visits) na
                        FROM fact_repair_jobs WHERE reported_date >= '2025-11-01' AND priority <> 'Emergency'
                        GROUP BY 1""", con).set_index("booking_channel")
avoidable_na = sum(last12.loc[c, "na"] - last12.loc[c, "jobs"] * portal_rate for c in ("Phone", "Email"))

# Extra return visits at Kestrel since January 2026 compared with its own earlier first-time-fix rate
k = pd.read_sql("""SELECT CASE WHEN reported_date < '2026-01-01' THEN 'before' ELSE 'after' END p,
                          COUNT(*) jobs, AVG(first_time_fix) ftf, SUM(completed_visits - 1) return_visits
                   FROM fact_repair_jobs WHERE contractor = 'Kestrel Property Services' AND status = 'Completed'
                   GROUP BY 1""", con).set_index("p")
extra_returns = k.loc["after", "return_visits"] - k.loc["after", "jobs"] * (k.loc["before", "return_visits"] / k.loc["before", "jobs"])

dm = res["damp_mould_monthly"]
wip = res["open_jobs_month_end"]
findings = {
    "sla_may_dec25": pct(early), "sla_jan_oct26": pct(late),
    "kestrel_sla_before": pct(early[early.contractor == K]), "kestrel_sla_after": pct(late[late.contractor == K]),
    "others_sla_before": pct(early[early.contractor != K]), "others_sla_after": pct(late[late.contractor != K]),
    "kestrel_ftf_before": 100 * k.loc["before", "ftf"], "kestrel_ftf_after": 100 * k.loc["after", "ftf"],
    "kestrel_extra_return_visits": float(extra_returns),
    "phone_no_access_per_job": float(na.loc["Phone", "no_access_visits_per_job"]),
    "portal_no_access_per_job": float(portal_rate),
    "portal_share_of_jobs": 100 * na.loc["Online portal", "jobs"] / na.jobs.sum(),
    "avoidable_no_access_visits_12m": float(avoidable_na),
    "no_access_visits_12m": float(year.no_access_visits),
    "return_visits_12m": float(year.return_visits),
    "repeat_reports_12m": float(year.repeat_reports),
    "jobs_12m": float(year.jobs_reported),
    "total_cost_12m": float(year.total_job_cost),
    "avg_cost_per_visit": float(year.avg_cost_per_visit),
    "damp_reports_may_oct25": float(dm[dm.month <= "2025-10"].reports.mean()),
    "damp_reports_nov25_sep26": float(dm[(dm.month >= "2025-11") & (dm.month <= "2026-09")].reports.mean()),
    "damp_visit14_first6": float(dm[dm.month <= "2025-10"].visited_within_14_days_pct.mean()),
    "damp_visit14_last5": float(dm[dm.month >= "2026-06"].visited_within_14_days_pct.mean()),
    "open_past_target_oct25": float(wip.iloc[5].open_past_target), "open_past_target_oct26": float(wip.iloc[-1].open_past_target),
    "open_jobs_oct25": float(wip.iloc[5].open_jobs), "open_jobs_oct26": float(wip.iloc[-1].open_jobs),
}
out = {"findings": {a: round(b, 2) for a, b in findings.items()},
       "cube": cube.to_dict("split")["data"],
       "scorecard": res["contractor_scorecard"].to_dict("records"),
       "no_access": res["no_access_by_channel"].to_dict("records"),
       "trades": res["first_time_fix_by_trade"].to_dict("records"),
       "damp": dm.to_dict("records"), "wip": wip.to_dict("records"),
       "satisfaction": res["satisfaction_by_outcome"].to_dict("records")}
os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "outputs", "dashboard_data.json"), "w"), separators=(",", ":"))
for name, df in res.items():
    df.to_csv(os.path.join(ROOT, "outputs", name + ".csv"), index=False)
for a, b in findings.items():
    print(f"{a:34s} {b:>12,.2f}")
