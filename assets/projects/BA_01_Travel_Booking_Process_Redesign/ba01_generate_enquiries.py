"""
Wren & Harbour Travel: synthetic enquiry log
--------------------------------------------
Eight weeks of holiday enquiries for a fictional independent travel agency (two branches, 11 consultants).
The data is synthetic. It is shaped to reflect four problems seen in a phone-and-spreadsheet booking process:
slow first response to written enquiries, quotes that are never followed up, the same details typed
several times, and booking errors that come from that retyping.

Run:  python ba01_generate_enquiries.py <output_folder>
"""
import sys, os
import numpy as np, pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(101)
days = pd.bdate_range("2026-08-31", "2026-10-24", freq="C", weekmask="Mon Tue Wed Thu Fri Sat")
consultants = ["Consultant " + c for c in "ABCDEFGHJKL"]
rows, eid = [], 9000
for d in days:
    for _ in range(rng.poisson(13 if d.dayofweek < 5 else 9)):
        eid += 1
        channel = rng.choice(["Phone", "Email", "Web form", "Walk-in", "Social media"], p=[.38, .22, .20, .12, .08])
        trip = rng.choice(["Package holiday", "Tailor-made", "Cruise", "Flights or hotel only"], p=[.42, .28, .12, .18])
        written = channel in ("Email", "Web form", "Social media")
        # first response: immediate in person or by phone; written enquiries wait in a shared inbox
        resp = float(rng.gamma(1.2, 0.2)) if not written else float(rng.gamma(1.6, 11.5))
        quoted = rng.random() < (0.93 if not written else 0.84)
        versions = int(1 + rng.poisson({"Tailor-made": 1.6, "Cruise": 0.9}.get(trip, 0.5))) if quoted else 0
        quote_hours = round(float(rng.gamma(2.0, {"Tailor-made": 16, "Cruise": 9}.get(trip, 5))), 1) if quoted else None
        follow = bool(quoted and rng.random() < 0.58)
        # chance of booking falls as the customer waits, and rises when a quote is chased
        p_book = 0.0
        if quoted:
            p_book = 0.30 * (1.0 if resp <= 2 else 0.78 if resp <= 8 else 0.55 if resp <= 24 else 0.36)
            p_book *= 1.45 if follow else 0.62
        booked = bool(rng.random() < p_book)
        value = round(float(rng.lognormal({"Tailor-made": 8.75, "Cruise": 8.6, "Package holiday": 7.95}.get(trip, 6.7), 0.45)), 2) if booked else None
        error = bool(booked and rng.random() < 0.085 + 0.02 * (versions - 1))
        admin_min = int(rng.normal(34, 8) + 9 * versions) if quoted else int(rng.normal(8, 3))
        rows.append((f"ENQ{eid}", d.date().isoformat(), channel, trip, rng.choice(consultants), round(resp, 1),
                     "Yes" if quoted else "No", quote_hours, versions, "Yes" if follow else "No",
                     "Yes" if booked else "No", value, "Yes" if error else "No", max(3, admin_min)))
cols = ["enquiry_id", "received_date", "channel", "trip_type", "consultant", "first_response_hours", "quote_sent",
        "quote_turnaround_hours", "quote_versions", "quote_followed_up", "booked", "booking_value_gbp",
        "booking_error", "admin_minutes"]
df = pd.DataFrame(rows, columns=cols)
df.to_csv(os.path.join(OUT, "enquiry_log.csv"), index=False)
w = df.channel.isin(["Email", "Web form", "Social media"])
q = df[df.quote_sent == "Yes"]
print(len(df), "enquiries")
print("conversion all %.1f | direct %.1f | written %.1f" % (100*(df.booked=="Yes").mean(), 100*(df[~w].booked=="Yes").mean(), 100*(df[w].booked=="Yes").mean()))
print("median first response: written %.1f h, direct %.1f h; written within 2h %.0f%%" % (df[w].first_response_hours.median(), df[~w].first_response_hours.median(), 100*(df[w].first_response_hours<=2).mean()))
print("quotes followed up %.0f%%; conv followed %.1f vs not %.1f" % (100*(q.quote_followed_up=="Yes").mean(), 100*(q[q.quote_followed_up=="Yes"].booked=="Yes").mean(), 100*(q[q.quote_followed_up=="No"].booked=="Yes").mean()))
b = df[df.booked=="Yes"]
print("bookings", len(b), "value", round(b.booking_value_gbp.sum()), "avg", round(b.booking_value_gbp.mean()), "errors %.1f%%" % (100*(b.booking_error=="Yes").mean()))
print("admin hours", round(df.admin_minutes.sum()/60), "quote TAT tailor-made median", q[q.trip_type=="Tailor-made"].quote_turnaround_hours.median())
for lo,hi in [(0,2),(2,8),(8,24),(24,999)]:
    s=df[(df.first_response_hours>lo)&(df.first_response_hours<=hi)] if lo else df[df.first_response_hours<=hi]
    print(f"resp {lo}-{hi}h: n={len(s)} conv={100*(s.booked=='Yes').mean():.1f}")
