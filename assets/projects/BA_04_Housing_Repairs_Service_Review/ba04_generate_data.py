"""
Soar Valley Homes: synthetic repairs dataset
--------------------------------------------
Soar Valley Homes is a fictional housing association with about 6,200 homes.
This script builds 18 months of responsive repairs jobs (May 2025 to October 2026).
The data is synthetic. Four service problems are built in for the analysis to find:

  1. One contractor (Kestrel) slows down and fixes less first time from January 2026.
  2. Damp and mould reports rise sharply from November 2025.
  3. Phone bookings have roughly double the no-access rate of portal bookings,
     which send a text reminder.
  4. Open work in progress grows because routine jobs take longer than they arrive.

Run:  python ba04_generate_data.py <output_folder>
"""
import sys, os, sqlite3
import numpy as np
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
rng = np.random.default_rng(404)
START, END = pd.Timestamp("2025-05-01"), pd.Timestamp("2026-10-31")

areas = ["North", "East", "South", "West"]
props = pd.DataFrame({"property_id": range(30001, 30001 + 6200)})
props["area"] = rng.choice(areas, len(props), p=[0.27, 0.24, 0.26, 0.23])
props["property_type"] = rng.choice(["Flat", "House", "Bungalow", "Maisonette"], len(props), p=[0.44, 0.38, 0.10, 0.08])
props["build_decade"] = rng.choice([1950, 1960, 1970, 1980, 1990, 2000, 2010], len(props), p=[.12, .2, .22, .16, .12, .1, .08])

trades = ["Plumbing", "Electrical", "Carpentry & Joinery", "Heating & Gas", "Damp & Mould", "Roofing & Guttering", "General"]
trade_p = np.array([0.24, 0.14, 0.15, 0.17, 0.06, 0.07, 0.17])
ftf_base = dict(zip(trades, [0.87, 0.89, 0.85, 0.81, 0.52, 0.64, 0.91]))
visit_cost = dict(zip(trades, [96, 88, 104, 118, 165, 172, 74]))
prio_by_trade = {  # Emergency, Urgent, Routine
    "Plumbing": [.16, .34, .50], "Electrical": [.18, .32, .50], "Carpentry & Joinery": [.04, .22, .74],
    "Heating & Gas": [.26, .44, .30], "Damp & Mould": [.03, .37, .60], "Roofing & Guttering": [.08, .32, .60],
    "General": [.02, .18, .80]}
TARGET = {"Emergency": 1, "Urgent": 7, "Routine": 28}

def mi(d):  # 0 = May 2025 ... 17 = Oct 2026
    return (d.year - 2025) * 12 + d.month - 5

season = {1: 1.22, 2: 1.15, 3: 1.05, 4: .95, 5: .9, 6: .86, 7: .84, 8: .86, 9: .95, 10: 1.05, 11: 1.15, 12: 1.2}
rows, jid = [], 700000
for d in pd.date_range(START, END, freq="D"):
    m = mi(d)
    n = rng.poisson(58 * season[d.month] * (0.35 if d.dayofweek >= 5 else 1.0))
    tp = trade_p.copy()
    if m >= 6:                                   # Problem 2: damp and mould reports rise from Nov 2025
        tp[4] *= 1.9
    tp = tp / tp.sum()
    pidx = rng.integers(len(props), size=n)
    for i in pidx:
        jid += 1
        pr = props.iloc[i]
        trade = trades[rng.choice(7, p=tp)]
        prio = ["Emergency", "Urgent", "Routine"][rng.choice(3, p=prio_by_trade[trade])]
        if trade == "Heating & Gas":
            contractor = "Calder Gas Services"
        elif pr.area in ("North", "East"):
            contractor = "Kestrel Property Services"
        else:
            contractor = "Direct Works Team"
        p_portal = 0.20 + 0.004 * m
        channel = rng.choice(["Phone", "Online portal", "Email"], p=[0.90 - p_portal, p_portal, 0.10])
        kestrel_bad = contractor == "Kestrel Property Services" and m >= 8      # Problem 1
        # wait for first appointment
        if prio == "Emergency":
            wait = int(rng.random() < 0.07)
        elif prio == "Urgent":
            wait = int(rng.gamma(2.2, 1.5)) + (int(rng.gamma(2, 1.6)) if kestrel_bad else 0)
        else:
            wait = int(rng.gamma(3.0, 4.6) * (1 + (0.085 * (m - 7) if kestrel_bad else 0)))
        first_visit = d + pd.Timedelta(days=wait)
        # Problem 3: no access depends on how the appointment was booked
        p_na = {"Phone": 0.19, "Online portal": 0.085, "Email": 0.165}[channel] * (0.25 if prio == "Emergency" else 1)
        no_access = 0
        t = first_visit
        while no_access < 3 and rng.random() < p_na:
            no_access += 1
            t = t + pd.Timedelta(days=int({"Emergency": 1, "Urgent": rng.integers(2, 5), "Routine": rng.integers(6, 13)}[prio]))
        ftf = rng.random() < (ftf_base[trade] - (0.11 if kestrel_bad else 0))
        visits = 1
        if not ftf:
            extra = 1 + int(rng.random() < 0.25)
            visits += extra
            t = t + pd.Timedelta(days=int(sum(rng.integers(5, 17) if prio != "Emergency" else rng.integers(1, 4) for _ in range(extra))))
        completed = t
        cost = visits * visit_cost[trade] * rng.uniform(0.8, 1.3) + no_access * 45
        repeat = rng.random() < (0.05 + (0.16 if not ftf else 0) + (0.14 if trade == "Damp & Mould" else 0))
        late = (completed - d).days > TARGET[prio]
        sat = None
        if rng.random() < 0.30:
            sat = int(np.clip(round(rng.normal(4.45 - 1.25 * late - 0.6 * (not ftf) - 0.35 * no_access, 0.7)), 1, 5))
        rows.append((jid, int(pr.property_id), pr.area, d, prio, TARGET[prio], trade, contractor, channel,
                     first_visit, no_access, visits, int(ftf), completed, int(repeat), round(cost, 2), sat))

jobs = pd.DataFrame(rows, columns=["job_id", "property_id", "area", "reported_date", "priority", "target_days", "trade",
                                   "contractor", "booking_channel", "first_visit_date", "no_access_visits",
                                   "completed_visits", "first_time_fix", "completed_date", "repeat_within_90_days",
                                   "job_cost", "satisfaction_score"])
# Jobs not finished by the reporting date are still open: no completion details yet
still_open = jobs.completed_date > END
for col in ["completed_date", "first_time_fix", "completed_visits", "job_cost", "satisfaction_score", "repeat_within_90_days"]:
    jobs.loc[still_open, col] = None
jobs.loc[jobs.first_visit_date > END, "first_visit_date"] = None
jobs["status"] = np.where(still_open, "Open", "Completed")

db = os.path.join(OUT, "data", "soar_valley_repairs.db")
if os.path.exists(db):
    os.remove(db)
con = sqlite3.connect(db)
for name, df in {"dim_property": props, "fact_repair_jobs": jobs}.items():
    df = df.copy()
    for c in df.columns:
        if c.endswith("_date"):
            df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
    for c in ("first_time_fix", "completed_visits", "repeat_within_90_days", "satisfaction_score"):
        if c in df:
            df[c] = df[c].astype("Int64")
    df.to_csv(os.path.join(OUT, "data", name + ".csv"), index=False)
    df.to_sql(name, con, index=False)
con.commit(); con.close()
print(len(jobs), "jobs;", int(still_open.sum()), "open at", END.date())
