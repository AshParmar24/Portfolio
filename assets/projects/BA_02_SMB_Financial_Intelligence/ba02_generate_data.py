"""
Harlow & Finch Trade Supplies: synthetic data generator
--------------------------------------------------------
Builds a reproducible two-year dataset for a fictional three-depot UK trade
wholesaler. The data is synthetic. Three commercial problems are deliberately
built in so the analysis has something real to find:

  1. Timber supplier costs rise from February 2026 and list prices do not follow.
  2. Discounting creeps up for two Nottingham sales reps on credit accounts.
  3. Trade-account customers pay later, and the Derby depot dispatches late
     from June 2026.

Run:  python ba02_generate_data.py <output_folder>
"""
import sys, os, sqlite3
import numpy as np
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
rng = np.random.default_rng(2026)

START, END = pd.Timestamp("2024-11-01"), pd.Timestamp("2026-10-31")
days = pd.date_range(START, END, freq="D")

# ---------------------------------------------------------------- dimensions
depots = pd.DataFrame({
    "depot_id": [1, 2, 3],
    "depot_name": ["Leicester", "Nottingham", "Derby"],
})

cats = {  # category: (products, price range, base margin, share of lines)
    "Timber & Sheet":      (26, (6, 85),  0.27, 0.26),
    "Plumbing & Heating":  (26, (3, 240), 0.33, 0.22),
    "Electrical":          (22, (2, 160), 0.35, 0.17),
    "Fixings & Tools":     (26, (2, 130), 0.38, 0.20),
    "Paint & Decorating":  (20, (4, 60),  0.34, 0.15),
}
rows, pid = [], 1000
for cat, (n, (lo, hi), margin, _) in cats.items():
    for _ in range(n):
        price = round(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), 2)
        m = float(np.clip(rng.normal(margin, 0.04), 0.15, 0.55))
        rows.append((pid, f"{cat.split(' ')[0][:3].upper()}-{pid}", cat, price, round(price * (1 - m), 2)))
        pid += 1
products = pd.DataFrame(rows, columns=["product_id", "sku", "category", "list_price", "base_unit_cost"])

reps = pd.DataFrame({
    "rep_id": range(1, 10),
    "rep_name": ["A. Okafor", "B. Whitlock", "C. Mistry", "D. Hale", "E. Purcell",
                 "F. Sandhu", "G. Lowry", "H. Brennan", "I. Castell"],
    "depot_id": [1, 1, 1, 2, 2, 2, 3, 3, 3],
})

segs = ["Trade Account", "Contractor", "Cash & Retail"]
n_cust = 640
cust = pd.DataFrame({
    "customer_id": range(5000, 5000 + n_cust),
    "segment": rng.choice(segs, n_cust, p=[0.30, 0.38, 0.32]),
    "depot_id": rng.choice([1, 2, 3], n_cust, p=[0.40, 0.33, 0.27]),
})
cust["payment_terms_days"] = cust["segment"].map({"Trade Account": 30, "Contractor": 30, "Cash & Retail": 0})
cust["rep_id"] = [int(rng.choice(reps.loc[reps.depot_id == d, "rep_id"])) for d in cust.depot_id]
# spend weight: a few large accounts dominate, as in most wholesalers
w = rng.pareto(1.6, n_cust) + 0.3
w[cust.segment.eq("Trade Account")] *= 2.4
w[cust.segment.eq("Cash & Retail")] *= 0.45
cust["_w"] = w / w.sum()

# ---------------------------------------------------------------- orders
def month_index(d):  # 0 for Nov 2024 ... 23 for Oct 2026
    return (d.year - 2024) * 12 + d.month - 11

season = {1: .82, 2: .88, 3: 1.0, 4: 1.08, 5: 1.12, 6: 1.12, 7: 1.08, 8: 1.0, 9: 1.05, 10: 1.04, 11: .95, 12: .72}
order_rows, line_rows = [], []
oid = 200000
cat_names = list(cats)
base_mix = np.array([cats[c][3] for c in cat_names])
prod_by_cat = {c: products[products.category == c] for c in cat_names}

for d in days:
    if d.dayofweek == 6:
        continue
    mi = month_index(d)
    growth = 1 + 0.07 * mi / 23
    n_orders = rng.poisson(27 * season[d.month] * growth * (0.55 if d.dayofweek == 5 else 1))
    chosen = rng.choice(n_cust, n_orders, p=cust["_w"].values)
    for ci in chosen:
        c = cust.iloc[ci]
        oid += 1
        # Problem 1 (mix): from spring 2026 more of the basket is timber
        mix = base_mix.copy()
        if mi >= 16:
            mix[0] *= 1.22
        mix = mix / mix.sum()
        n_lines = 1 + rng.poisson(1.7 if c.segment != "Cash & Retail" else 0.8)
        order_rows.append((oid, d, int(c.customer_id), int(c.depot_id), int(c.rep_id)))
        for ln in range(1, n_lines + 1):
            cat = cat_names[rng.choice(5, p=mix)]
            p = prod_by_cat[cat].iloc[rng.integers(len(prod_by_cat[cat]))]
            qty = int(max(1, rng.gamma(2.0, {"Trade Account": 9, "Contractor": 5, "Cash & Retail": 1.6}[c.segment])))
            # base discount by segment
            disc = {"Trade Account": 0.08, "Contractor": 0.05, "Cash & Retail": 0.01}[c.segment]
            disc += rng.normal(0, 0.012)
            # Problem 2 (discount creep): reps 5 and 6, credit accounts, from Dec 2025
            if c.rep_id in (5, 6) and c.segment != "Cash & Retail" and mi >= 13:
                disc += min(0.09, 0.012 * (mi - 12))
            disc = float(np.clip(disc, 0, 0.30))
            # list price: one modest 2 percent rise in April 2026, none on timber
            lp = p.list_price * (1.02 if (mi >= 17 and cat != "Timber & Sheet") else 1.0)
            # Problem 1 (cost): timber supplier cost up 13 percent from Feb 2026, others drift 2 percent
            cost = p.base_unit_cost * ((1.13 if mi >= 15 else 1.0) if cat == "Timber & Sheet"
                                       else (1.02 if mi >= 17 else 1.0))
            line_rows.append((oid, ln, int(p.product_id), qty, round(lp, 2), round(disc, 4), round(cost, 2)))

orders = pd.DataFrame(order_rows, columns=["order_id", "order_date", "customer_id", "depot_id", "rep_id"])
lines = pd.DataFrame(line_rows, columns=["order_id", "line_no", "product_id", "quantity",
                                         "list_price", "discount_pct", "unit_cost"])
lines["net_revenue"] = (lines.quantity * lines.list_price * (1 - lines.discount_pct)).round(2)
lines["cost_of_sales"] = (lines.quantity * lines.unit_cost).round(2)

# ---------------------------------------------------------------- invoices (cash collection)
o = orders.merge(cust[["customer_id", "segment", "payment_terms_days", "_w"]], on="customer_id")
o["amount"] = lines.groupby("order_id").net_revenue.sum().reindex(o.order_id).values
mi_arr = o.order_date.map(month_index).values
big = o["_w"].values >= np.sort(cust["_w"].values)[-40]          # the 40 largest accounts
late = np.where(o.segment.eq("Trade Account"),
                rng.gamma(2.0, 4.5, len(o)) + np.where((mi_arr >= 12) & big, (mi_arr - 11) * 2.3, 0),
                np.where(o.segment.eq("Contractor"), rng.gamma(2.0, 3.5, len(o)), 0))
o["due_date"] = o.order_date + pd.to_timedelta(o.payment_terms_days, unit="D")
o["paid_date"] = o.due_date + pd.to_timedelta(np.round(late).astype(int), unit="D")
o.loc[o.paid_date > END, "paid_date"] = pd.NaT                   # still unpaid at the reporting date
invoices = o[["order_id", "order_date", "due_date", "paid_date", "amount"]].rename(
    columns={"order_date": "invoice_date", "order_id": "order_id"})
invoices.insert(0, "invoice_id", ["INV" + str(x) for x in invoices.order_id])

# ---------------------------------------------------------------- deliveries (fulfilment)
dl = orders[orders.customer_id.isin(cust.loc[cust.segment != "Cash & Retail", "customer_id"])].copy()
dl = dl[rng.random(len(dl)) < 0.72]                              # the rest are collected at the counter
mi_d = dl.order_date.map(month_index).values
p_late = np.where((dl.depot_id.values == 3) & (mi_d >= 19), 0.07 + 0.035 * (mi_d - 18), 0.065)
is_late = rng.random(len(dl)) < p_late
dl["promised_date"] = dl.order_date + pd.Timedelta(days=2)
dl["dispatched_date"] = dl.promised_date - pd.Timedelta(days=1) + pd.to_timedelta(
    np.where(is_late, rng.integers(2, 6, len(dl)), 0), unit="D")
dl["delivered_date"] = dl.dispatched_date + pd.Timedelta(days=1)
dl["complete_flag"] = (rng.random(len(dl)) > np.where((dl.depot_id.values == 3) & (mi_d >= 19), 0.07, 0.03)).astype(int)
deliveries = dl[["order_id", "depot_id", "promised_date", "dispatched_date", "delivered_date", "complete_flag"]]

# ---------------------------------------------------------------- write CSV + SQLite
cust_out = cust.drop(columns="_w")
tables = {
    "dim_depot": depots, "dim_product": products, "dim_rep": reps, "dim_customer": cust_out,
    "fact_orders": orders, "fact_order_lines": lines, "fact_invoices": invoices, "fact_deliveries": deliveries,
}
db = os.path.join(OUT, "data", "harlow_finch.db")
if os.path.exists(db):
    os.remove(db)
con = sqlite3.connect(db)
for name, df in tables.items():
    df = df.copy()
    for col in df.columns:
        if "date" in col:
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
    df.to_csv(os.path.join(OUT, "data", name + ".csv"), index=False)
    df.to_sql(name, con, index=False)
con.commit()
con.close()
for name, df in tables.items():
    print(f"{name:18s} {len(df):>7,} rows")
