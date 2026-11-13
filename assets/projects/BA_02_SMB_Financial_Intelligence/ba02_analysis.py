"""
Harlow & Finch Trade Supplies: analysis pipeline
------------------------------------------------
1. Runs every named query in ba02_kpi_queries.sql against the SQLite database.
2. Builds the gross profit bridge (FY25 to FY26) at product level.
3. Sizes each finding in pounds.
4. Writes the dashboard data file and the flat extracts used for Tableau.

Run:  python ba02_analysis.py <project_folder>
"""
import sys, os, json, sqlite3
import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
con = sqlite3.connect(os.path.join(ROOT, "data", "harlow_finch.db"))
here = os.path.dirname(os.path.abspath(__file__))
sql_path = os.path.join(ROOT, "ba02_kpi_queries.sql")
if not os.path.exists(sql_path):
    sql_path = os.path.join(here, "ba02_kpi_queries.sql")

# ---- 1. run the named queries
results = {}
for block in open(sql_path).read().split("-- name: ")[1:]:
    name, body = block.split("\n", 1)
    results[name.strip()] = pd.read_sql(body, con)

# ---- 2. gross profit bridge at product level
lines = pd.read_sql("""
    SELECT l.product_id, p.category, o.rep_id,
           CASE WHEN o.order_date < '2025-11-01' THEN 'FY25' ELSE 'FY26' END AS fy,
           l.quantity AS q, l.quantity * l.list_price AS list_value,
           l.net_revenue AS rev, l.cost_of_sales AS cos
    FROM fact_order_lines l
    JOIN fact_orders o ON o.order_id = l.order_id
    JOIN dim_product p ON p.product_id = l.product_id""", con)

g = lines.groupby(["product_id", "category", "fy"])[["q", "list_value", "rev", "cos"]].sum().unstack("fy")
g.columns = [f"{a}_{b}" for a, b in g.columns]
g = g.reset_index()
for y in ("FY25", "FY26"):
    g[f"list_{y}"] = g[f"list_value_{y}"] / g[f"q_{y}"]          # average list price per unit
    g[f"disc_{y}"] = (g[f"list_value_{y}"] - g[f"rev_{y}"]) / g[f"q_{y}"]   # discount given per unit
    g[f"cost_{y}"] = g[f"cos_{y}"] / g[f"q_{y}"]                 # cost per unit
    g[f"margin_{y}"] = g[f"list_{y}"] - g[f"disc_{y}"] - g[f"cost_{y}"]

gp25 = (g.rev_FY25 - g.cos_FY25).sum()
gp26 = (g.rev_FY26 - g.cos_FY26).sum()
# Unit margin change splits exactly into list price, discount and cost. Each is valued at FY26 volumes.
price_fx = (g.q_FY26 * (g.list_FY26 - g.list_FY25)).sum()
disc_fx = -(g.q_FY26 * (g.disc_FY26 - g.disc_FY25)).sum()
cost_fx = -(g.q_FY26 * (g.cost_FY26 - g.cost_FY25)).sum()
vol_mix = ((g.q_FY26 - g.q_FY25) * g.margin_FY25).sum()
# Volume is growth at constant FY25 net prices applied to FY25 profit. Mix is what is left of volume and mix.
net25 = g.rev_FY25 / g.q_FY25
volume_fx = gp25 * ((g.q_FY26 * net25).sum() / g.rev_FY25.sum() - 1)
mix_fx = vol_mix - volume_fx
bridge = [("FY25 gross profit", gp25), ("Volume", volume_fx), ("Product mix", mix_fx), ("List price", price_fx),
          ("Discounting", disc_fx), ("Supplier cost", cost_fx), ("FY26 gross profit", gp26)]
assert abs(gp25 + volume_fx + mix_fx + price_fx + disc_fx + cost_fx - gp26) < 1, "bridge does not reconcile"

# ---- 3. size the findings
timber = g[g.category == "Timber & Sheet"]
timber_cost_hit = (timber.q_FY26 * (timber.cost_FY26 - timber.cost_FY25)).sum()
# Timber sold since the cost rise (Feb to Oct 2026), valued at list: a price rise of x percent recovers x percent of this
tim_since = pd.read_sql("""SELECT SUM(l.quantity*l.list_price) lv, SUM(l.net_revenue) rev, SUM(l.cost_of_sales) cos
    FROM fact_order_lines l JOIN fact_orders o ON o.order_id=l.order_id JOIN dim_product p ON p.product_id=l.product_id
    WHERE p.category='Timber & Sheet' AND o.order_date>='2026-02-01'""", con).iloc[0]
rep = results["discount_by_rep_year"].set_index("rep_name")
flag = rep.loc[["E. Purcell", "F. Sandhu"]]
excess_disc = float((flag.list_value_fy26 * (flag.discount_pct_fy26 - flag.discount_pct_fy25) / 100).sum())
dtp = results["days_to_pay_monthly"]
ta = dtp[dtp.segment == "Trade Account"].set_index("month")
dtp_fy25 = (ta.loc["2024-11":"2025-10", "avg_days_to_pay"] * ta.loc["2024-11":"2025-10", "invoiced_value"]).sum() / ta.loc["2024-11":"2025-10", "invoiced_value"].sum()
recent = ta.loc["2026-06":"2026-08"]
dtp_recent = (recent.avg_days_to_pay * recent.invoiced_value).sum() / recent.invoiced_value.sum()
daily_trade_sales = recent.invoiced_value.sum() / 92
cash_tied = (dtp_recent - dtp_fy25) * daily_trade_sales
otif = results["otif_monthly_by_depot"]
def otif_rate(df):
    return 100 * df.on_time_in_full.sum() / df.deliveries.sum()
derby = otif[otif.depot == "Derby"].set_index("month")
others = otif[otif.depot != "Derby"].set_index("month")

head = results["kpi_headline_by_year"].set_index("fin_year")
findings = {
    "revenue_fy25": float(head.loc["FY25", "revenue"]), "revenue_fy26": float(head.loc["FY26", "revenue"]),
    "gp_fy25": float(gp25), "gp_fy26": float(gp26),
    "gm_fy25": float(head.loc["FY25", "gross_margin_pct"]), "gm_fy26": float(head.loc["FY26", "gross_margin_pct"]),
    "disc_fy25": float(head.loc["FY25", "avg_discount_pct"]), "disc_fy26": float(head.loc["FY26", "avg_discount_pct"]),
    "timber_cost_hit_fy26": float(timber_cost_hit),
    "timber_list_value_feb_oct26": float(tim_since.lv),
    "timber_margin_feb_oct26": float(100 * (tim_since.rev - tim_since.cos) / tim_since.rev),
    "timber_annualised_cost_hit": float(timber_cost_hit * 12 / 9),
    "excess_discount_fy26": excess_disc,
    "trade_days_to_pay_fy25": float(dtp_fy25), "trade_days_to_pay_jun_aug26": float(dtp_recent),
    "cash_tied_up": float(cash_tied),
    "derby_otif_before": float(otif_rate(derby.loc[:"2026-05"])), "derby_otif_jun_oct26": float(otif_rate(derby.loc["2026-06":])),
    "derby_otif_oct26": float(otif_rate(derby.loc["2026-10":])),
    "other_otif_jun_oct26": float(otif_rate(others.loc["2026-06":])),
}

# ---- 4. outputs
out = {
    "bridge": [{"step": s, "value": round(float(v))} for s, v in bridge],
    "findings": {k: round(v, 2) for k, v in findings.items()},
    "sales": results["sales_cube_monthly"].round(0).to_dict("split")["data"],
    "category": results["margin_by_category_year"].to_dict("records"),
    "timber": results["timber_cost_vs_price"].to_dict("records"),
    "reps": results["discount_by_rep_year"].to_dict("records"),
    "rep_trend": results["discount_trend_flagged_reps"].to_dict("records"),
    "days_to_pay": dtp[dtp.month <= "2026-08"].to_dict("records"),
    "aged_debt": results["aged_debt_snapshot"].to_dict("records"),
    "late_payers": results["late_payers_top_accounts"].to_dict("records"),
    "otif": otif.to_dict("records"),
}
os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "outputs", "dashboard_data.json"), "w"), separators=(",", ":"))
for name, df in results.items():
    df.to_csv(os.path.join(ROOT, "outputs", name + ".csv"), index=False)
pd.DataFrame(bridge, columns=["step", "value_gbp"]).round(0).to_csv(os.path.join(ROOT, "outputs", "gross_profit_bridge.csv"), index=False)

print("Gross profit bridge")
for s, v in bridge:
    print(f"  {s:20s} {v:>12,.0f}")
for k, v in findings.items():
    print(f"  {k:32s} {v:>14,.2f}")
