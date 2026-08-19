#!/usr/bin/env python3
"""
Doorstep — Track A "Service as a Service" simulated dataset generator
=====================================================================
Generates one interlocking, internally-consistent dataset that feeds all
20 Track A modules (A01-A20).

Design principles
-----------------
* One source of truth. bookings.csv is the spine; every other file is
  derived from or joins cleanly onto it (same IDs, same dates, same crews).
* Realistic structure, not noise. Demand has a weekly cycle, festival
  spikes, weather sensitivity and a slow growth trend. No-shows are a
  realistic minority. Ratings depend on crew skill + lateness.
* Honest imperfection. A few missing values and a mild class imbalance
  are left in on purpose — the guidebooks explicitly ask students to
  handle these (A11 no-show imbalance, A05 low-data early hours).
* Reproducible. Fixed SEED. Re-run to regenerate identically; change the
  seed to give a different cohort a fresh-but-equivalent dataset.

Author: Faculty (Synergy / Thematic Assessment). Fictional company.
"""

import csv, json, math, random, os, datetime as dt
from collections import defaultdict

SEED = 7
random.seed(SEED)

OUT = os.environ.get("DOORSTEP_OUT", "/home/claude/doorstep_track_a")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------
# 0. Calendar & city
# ----------------------------------------------------------------------
START = dt.date(2024, 1, 1)
END   = dt.date(2025, 12, 31)          # ~2 years, daily
DAYS  = (END - START).days + 1
ALL_DATES = [START + dt.timedelta(days=i) for i in range(DAYS)]

# A fictional city grid (roughly Gurugram-sized) in lat/lng.
CITY_LAT, CITY_LNG = 28.4595, 77.0266
# Named demand hotspots (office parks, residential clusters) -> (lat, lng, weight, zone)
HOTSPOTS = [
    ("Cyber Hub",        28.4949, 77.0880, 3.0, "north"),
    ("Golf Course Road", 28.4420, 77.1025, 2.5, "north"),
    ("Sohna Road",       28.4089, 77.0378, 2.0, "south"),
    ("Udyog Vihar",      28.5030, 77.0870, 1.8, "north"),
    ("Sector 56",        28.4211, 77.1010, 1.5, "east"),
    ("Palam Vihar",      28.5110, 77.0350, 1.6, "west"),
    ("Manesar",          28.3540, 76.9370, 1.2, "south"),
    ("DLF Phase 3",      28.4930, 77.0960, 2.2, "north"),
    ("Sector 14",        28.4700, 77.0300, 1.4, "west"),
    ("New Gurgaon",      28.4200, 76.9800, 1.3, "west"),
]
ZONES = ["north", "south", "east", "west"]

def sample_location():
    """Pick a hotspot by weight, then jitter around it (gaussian, ~2km)."""
    total = sum(h[3] for h in HOTSPOTS)
    r = random.uniform(0, total)
    acc = 0
    for name, lat, lng, w, zone in HOTSPOTS:
        acc += w
        if r <= acc:
            jlat = lat + random.gauss(0, 0.012)
            jlng = lng + random.gauss(0, 0.012)
            return round(jlat, 5), round(jlng, 5), zone, name
    h = HOTSPOTS[0]
    return round(h[1], 5), round(h[2], 5), h[4], h[0]

def haversine_km(a_lat, a_lng, b_lat, b_lng):
    R = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dl = math.radians(b_lng - a_lng)
    x = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.asin(math.sqrt(x))

# ----------------------------------------------------------------------
# 1. Holidays & festivals (drives demand spikes / dips) -> holidays.csv
# ----------------------------------------------------------------------
# (month, day, name, demand_multiplier). Multiplier >1 = pre-festival wash rush,
# <1 = holiday itself (people away / crews off).
FESTIVALS = [
    (1, 26, "Republic Day", 0.75),
    (3, 25, "Holi", 0.60),
    (3, 24, "Holi Eve (pre-wash rush)", 1.35),
    (8, 15, "Independence Day", 0.80),
    (10, 2, "Gandhi Jayanti", 0.85),
    (10, 20, "Karva Chauth", 1.15),
    (11, 1, "Diwali (pre-wash rush)", 1.55),
    (11, 2, "Diwali", 0.45),
    (11, 3, "Diwali Holiday", 0.55),
    (12, 25, "Christmas", 0.80),
    (12, 31, "New Year Eve", 1.20),
]
def holiday_lookup():
    m = {}
    for mm, dd, name, mult in FESTIVALS:
        for y in (2024, 2025):
            try:
                m[dt.date(y, mm, dd)] = (name, mult)
            except ValueError:
                pass
    return m
HOLIDAYS = holiday_lookup()

# ----------------------------------------------------------------------
# 2. Weather (monsoon dips wash demand) -> weather.csv
# ----------------------------------------------------------------------
def weather_for(d):
    """Return (temp_c, rain_mm, condition). Delhi-NCR-like seasonality."""
    doy = d.timetuple().tm_yday
    # temperature: cold Jan, hot May-Jun, mild post-monsoon
    temp = 25 - 11*math.cos(2*math.pi*(doy-15)/365) + random.gauss(0, 2.2)
    temp = round(temp, 1)
    # monsoon window ~ Jul-mid Sep => higher rain probability
    monsoon = 1 if 182 <= doy <= 258 else 0
    p_rain = 0.42 if monsoon else 0.06
    if random.random() < p_rain:
        rain = round(abs(random.gauss(18 if monsoon else 6, 12)), 1)
    else:
        rain = 0.0
    if rain > 25:
        cond = "heavy_rain"
    elif rain > 2:
        cond = "rain"
    elif temp > 40:
        cond = "heatwave"
    elif temp < 8:
        cond = "cold"
    else:
        cond = "clear"
    return temp, rain, cond

WEATHER = {d: weather_for(d) for d in ALL_DATES}

# ----------------------------------------------------------------------
# 3. Staff / crews -> staff.csv
# ----------------------------------------------------------------------
# 14 crews. Each: home base, skill (detailing) 1-5, speed factor, base area,
# join date (some join mid-history -> feeds A20 "new joiner" analysis & A09 tenure).
FIRST = ["Aarav","Vivaan","Kabir","Rohan","Ishaan","Arjun","Reyansh","Dev",
         "Manav","Yash","Kunal","Sahil","Nikhil","Aryan","Farhan","Imran",
         "Zaid","Karan","Tarun","Gaurav"]
LAST  = ["Sharma","Verma","Singh","Gupta","Khan","Yadav","Malik","Rana",
         "Chauhan","Mehta","Sethi","Ahuja","Bansal","Rao"]

def make_staff(n=14):
    crews = []
    used = set()
    for i in range(1, n+1):
        while True:
            nm = f"{random.choice(FIRST)} {random.choice(LAST)}"
            if nm not in used:
                used.add(nm); break
        base = random.choice(HOTSPOTS)
        # Most crews present from the start; 4 join later (for A20 fairness).
        if i <= n-4:
            join = START
        else:
            join = START + dt.timedelta(days=random.randint(120, 560))
        skill = random.choices([2,3,4,5], weights=[2,4,3,2])[0]
        crews.append({
            "crew_id": f"C{i:02d}",
            "crew_name": nm,
            "home_lat": round(base[1] + random.gauss(0, 0.01), 5),
            "home_lng": round(base[2] + random.gauss(0, 0.01), 5),
            "home_zone": base[4],
            "detailing_skill": skill,          # 1-5, affects rating & A08 matching
            "speed_factor": round(random.uniform(0.85, 1.15), 2),  # <1 faster
            "join_date": join.isoformat(),
            "shift_start": random.choice(["08:00","08:00","09:00"]),
            "shift_end": random.choice(["18:00","19:00","18:00"]),
        })
    return crews

STAFF = make_staff()
STAFF_BY_ID = {s["crew_id"]: s for s in STAFF}

def active_crews_on(d):
    return [s for s in STAFF if dt.date.fromisoformat(s["join_date"]) <= d]

# ----------------------------------------------------------------------
# 4. Service catalogue (slots, add-ons) -> services reference in dict
# ----------------------------------------------------------------------
SLOT_TYPES = [   # slot_type, base_price, base_minutes, weekend_premium
    ("exterior",        349, 35, 1.15),
    ("exterior_plus",   499, 45, 1.20),
    ("interior",        399, 40, 1.10),
    ("full_detail",     999, 90, 1.25),
    ("subscription",    299, 35, 1.00),   # subscriber's included wash
]
ADDONS = [   # item, price, attach_probability, minutes
    ("interior_clean", 250, 0.28, 20),
    ("wax_polish",     400, 0.16, 25),
    ("tyre_dressing",   99, 0.34, 5),
    ("pet_hair",       150, 0.07, 15),
    ("engine_bay",     350, 0.05, 20),
]

# ----------------------------------------------------------------------
# 5. Customers -> customers.csv  (subscribers + one-off)
# ----------------------------------------------------------------------
N_CUSTOMERS = 2600
def make_customers(n=N_CUSTOMERS):
    custs = []
    for i in range(1, n+1):
        lat, lng, zone, hs = sample_location()
        is_sub = random.random() < 0.34
        signup = START + dt.timedelta(days=random.randint(0, DAYS-30))
        vehicle_size = random.choices(["hatchback","sedan","suv"],
                                      weights=[4,4,3])[0]
        custs.append({
            "customer_id": f"U{i:05d}",
            "home_lat": lat, "home_lng": lng, "zone": zone, "area": hs,
            "is_subscriber": int(is_sub),
            "signup_date": signup.isoformat(),
            "vehicle_size": vehicle_size,
            # latent traits (NOT exported directly except where a module needs them)
            "_reliability": random.betavariate(9, 1.2),   # ~0.88 mean -> no-show
            "_price_sensitivity": round(random.uniform(0.4, 1.6), 2),
            "_base_satisfaction": random.uniform(3.3, 4.7),
            "_churn_prone": random.random() < 0.22,
        })
    return custs

CUSTOMERS = make_customers()
SUBSCRIBERS = [c for c in CUSTOMERS if c["is_subscriber"]]

# ----------------------------------------------------------------------
# 6. Demand model -> daily booking count
# ----------------------------------------------------------------------
def base_demand(d, idx):
    dow = d.weekday()  # 0 Mon .. 6 Sun
    # weekly shape: weekend heavy, midweek light (matches A03 "Sat sells out")
    weekly = {0:0.85, 1:0.80, 2:0.78, 3:0.86, 4:1.05, 5:1.55, 6:1.40}[dow]
    # slow growth trend over two years (company scaling)
    trend = 1.0 + 0.45 * (idx / DAYS)
    # annual seasonality: spring & autumn peaks, monsoon & peak-summer dips
    doy = d.timetuple().tm_yday
    seasonal = 1.0 + 0.18*math.sin(2*math.pi*(doy-80)/365)
    base = 46 * weekly * trend * seasonal
    # weather effect
    temp, rain, cond = WEATHER[d]
    if cond == "heavy_rain": base *= 0.45
    elif cond == "rain":     base *= 0.72
    elif cond == "heatwave": base *= 0.9
    # festival effect
    if d in HOLIDAYS:
        base *= HOLIDAYS[d][1]
    # noise
    base *= random.gauss(1.0, 0.08)
    return max(3, int(round(base)))

# ----------------------------------------------------------------------
# 7. Build bookings + jobs_done + supporting rows
# ----------------------------------------------------------------------
bookings = []
jobs_done = []
noshow_count = 0
booking_seq = 0

# planted anomalies for A17 (surge-alarm answer key)
PLANTED_ANOMALIES = {}
# a genuine demand surge (heatwave dust event) and a data glitch (double-logged day)
surge_day = dt.date(2025, 5, 12)
glitch_day = dt.date(2024, 9, 3)
PLANTED_ANOMALIES[surge_day.isoformat()] = "real_surge"
PLANTED_ANOMALIES[glitch_day.isoformat()] = "data_glitch"

SLOT_WEIGHTS = [0.34, 0.14, 0.20, 0.08, 0.24]  # aligns with SLOT_TYPES order

for idx, d in enumerate(ALL_DATES):
    n = base_demand(d, idx)
    if d == surge_day:
        n = int(n * 2.3)            # real surge
    crews_today = active_crews_on(d)
    temp, rain, cond = WEATHER[d]
    is_weekend = d.weekday() >= 5

    day_rows = []
    for _ in range(n):
        booking_seq += 1
        bid = f"B{booking_seq:06d}"
        # customer: subscribers rebook more often
        if SUBSCRIBERS and random.random() < 0.45:
            cust = random.choice(SUBSCRIBERS)
        else:
            cust = random.choice(CUSTOMERS)
        # subscribers usually take the subscription slot
        if cust["is_subscriber"] and random.random() < 0.7:
            slot = SLOT_TYPES[4]
        else:
            slot = random.choices(SLOT_TYPES, weights=SLOT_WEIGHTS)[0]
        slot_type, base_price, base_min, wk_prem = slot
        price = base_price * (wk_prem if is_weekend else 1.0)
        # morning slots more popular
        hour = random.choices(range(8, 19),
            weights=[10,12,11,9,7,6,7,8,9,7,5])[0]
        minute = random.choice([0, 30])
        slot_time = f"{hour:02d}:{minute:02d}"

        # add-ons -> items list
        items = [slot_type]
        addon_revenue = 0
        for item, ap, prob, amn in ADDONS:
            if random.random() < prob:
                items.append(item)
                addon_revenue += ap
        total_price = round(price + addon_revenue, 0)

        # no-show model: depends on customer reliability, weather, lead
        p_noshow = (1 - cust["_reliability"]) * 0.35
        if cond in ("rain","heavy_rain"): p_noshow += 0.03
        if slot_type == "subscription": p_noshow *= 0.6
        is_noshow = random.random() < p_noshow
        if is_noshow:
            noshow_count += 1

        crew = random.choice(crews_today)
        # travel/duration
        dist_km = haversine_km(crew["home_lat"], crew["home_lng"],
                               cust["home_lat"], cust["home_lng"])
        minutes = int(round(base_min * crew["speed_factor"]
                            + sum(a[3] for a in ADDONS if a[0] in items)))
        # lateness -> lower rating (feeds A08 ratings, A15 review sentiment)
        late_min = max(0, int(random.gauss(dist_km*1.4 - 6, 8)))
        # water usage (A07): by vehicle size & dirtiness; capped realism
        size_factor = {"hatchback":1.0,"sedan":1.2,"suv":1.5}[cust["vehicle_size"]]
        dirtiness = random.choices([1,2,3,4], weights=[2,4,3,1])[0]  # A14 dirt levels
        water_l = round((28 + 6*dirtiness) * size_factor
                        + (18 if "interior_clean" in items else 0)
                        + random.gauss(0,3), 1)
        water_l = max(15.0, water_l)

        status = "no_show" if is_noshow else "completed"

        row = {
            "booking_id": bid,
            "date": d.isoformat(),
            "slot_time": slot_time,
            "customer_id": cust["customer_id"],
            "crew_id": crew["crew_id"],
            "zone": cust["zone"],
            "area": cust["area"],
            "lat": cust["home_lat"],
            "lng": cust["home_lng"],
            "slot_type": slot_type,
            "items": "|".join(items),
            "vehicle_size": cust["vehicle_size"],
            "list_price": round(price, 0),
            "total_price": total_price,
            "is_weekend": int(is_weekend),
            "status": status,
        }
        bookings.append(row)
        day_rows.append(row)

        # jobs_done only for completed jobs
        if not is_noshow:
            # rating: skill up, lateness down, base satisfaction, noise
            rating = (cust["_base_satisfaction"]
                      + (crew["detailing_skill"] - 3) * 0.28
                      - min(late_min, 40) * 0.035
                      + random.gauss(0, 0.35))
            rating = max(1, min(5, round(rating)))
            arrival_h = hour + (minute + late_min) / 60.0
            jobs_done.append({
                "booking_id": bid,
                "date": d.isoformat(),
                "crew_id": crew["crew_id"],
                "customer_id": cust["customer_id"],
                "zone": cust["zone"],
                "scheduled_time": slot_time,
                "arrival_time": f"{int(arrival_h)%24:02d}:{int((arrival_h%1)*60):02d}",
                "late_minutes": late_min,
                "duration_minutes": minutes,
                "distance_km": round(dist_km, 2),
                "water_litres": water_l,
                "dirtiness_level": dirtiness,
                "rating": rating,
                "revenue": total_price,
            })

# data glitch: duplicate ~40% of glitch_day rows with new IDs (A17 must catch it as non-real).
# Duplicates are marked status="duplicate" so a bookings<->jobs_done join stays clean;
# A17 (surge alarm) works from raw daily counts, where the inflated count is the tell.
glitch_rows = [r for r in bookings if r["date"] == glitch_day.isoformat()
               and r["status"] == "completed"]
for r in glitch_rows[: int(len(glitch_rows)*0.4)]:
    booking_seq += 1
    dup = dict(r)
    dup["booking_id"] = f"B{booking_seq:06d}"
    dup["status"] = "duplicate"
    bookings.append(dup)

# inject a few honest missing values (A11/A05/A02 must handle these)
miss = random.sample(bookings, k=int(len(bookings)*0.008))
for r in miss:
    r["total_price"] = ""   # missing price

print(f"bookings: {len(bookings):,}  |  jobs_done: {len(jobs_done):,}  "
      f"|  no-shows: {noshow_count:,} ({noshow_count/len(bookings)*100:.1f}%)")

# ----------------------------------------------------------------------
# 8. Aggregate customer table with churn label -> customers.csv (A08/A09/A18)
# ----------------------------------------------------------------------
last_booking = {}
book_counts = defaultdict(int)
complaints = defaultdict(int)
ratings_by_cust = defaultdict(list)
for j in jobs_done:
    book_counts[j["customer_id"]] += 1
    ratings_by_cust[j["customer_id"]].append(j["rating"])
    if j["rating"] <= 2:
        complaints[j["customer_id"]] += 1
for b in bookings:
    d = b["date"]
    cid = b["customer_id"]
    if cid not in last_booking or d > last_booking[cid]:
        last_booking[cid] = d

customers_out = []
for c in CUSTOMERS:
    cid = c["customer_id"]
    lb = last_booking.get(cid)
    days_since = (END - dt.date.fromisoformat(lb)).days if lb else None
    # churn label: subscriber with no booking in 60d before END. Churn-prone
    # customers and those with low ratings / complaints are more likely.
    if c["is_subscriber"]:
        ratings_c = ratings_by_cust.get(cid, [])
        avg_r = sum(ratings_c)/len(ratings_c) if ratings_c else 3.0
        p = 0.10
        if c["_churn_prone"]: p += 0.35
        if days_since is not None and days_since > 60: p += 0.30
        if avg_r < 3.2: p += 0.20
        if complaints.get(cid, 0) >= 2: p += 0.15
        churned = int(random.random() < min(p, 0.95))
    else:
        churned = ""   # churn only defined for subscribers (A09 must decide scope)
    ratings = ratings_by_cust.get(cid, [])
    customers_out.append({
        "customer_id": cid,
        "signup_date": c["signup_date"],
        "zone": c["zone"], "area": c["area"],
        "home_lat": c["home_lat"], "home_lng": c["home_lng"],
        "vehicle_size": c["vehicle_size"],
        "is_subscriber": c["is_subscriber"],
        "total_bookings": book_counts.get(cid, 0),
        "avg_rating": round(sum(ratings)/len(ratings), 2) if ratings else "",
        "complaints": complaints.get(cid, 0),
        "days_since_last_booking": days_since if days_since is not None else "",
        "churned": churned,
    })

# ----------------------------------------------------------------------
# 9. Vehicles / cost & emission factors -> vehicles.csv (A07, A12)
# ----------------------------------------------------------------------
vehicles = [
    # type, capacity_litres, purchase_cost_inr, fuel_cost_per_km, co2_g_per_km, crew_size
    ("small_van",  200,  850000, 8.5, 180, 2),
    ("large_van",  350, 1200000, 11.0, 240, 2),
    ("ev_van",     280, 1600000, 3.2,  40, 2),
]

# ----------------------------------------------------------------------
# 10. Write everything
# ----------------------------------------------------------------------
def write_csv(name, rows, fields):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return path

# bookings.csv
write_csv("bookings.csv", bookings, list(bookings[0].keys()))

# jobs_done.csv
write_csv("jobs_done.csv", jobs_done, list(jobs_done[0].keys()))

# staff.csv (drop nothing; latent-free already)
write_csv("staff.csv", STAFF, list(STAFF[0].keys()))

# customers.csv
write_csv("customers.csv", customers_out, list(customers_out[0].keys()))

# weather.csv
weather_rows = [{"date": d.isoformat(), "temp_c": WEATHER[d][0],
                 "rain_mm": WEATHER[d][1], "condition": WEATHER[d][2]}
                for d in ALL_DATES]
write_csv("weather.csv", weather_rows, ["date","temp_c","rain_mm","condition"])

# holidays.csv
hol_rows = [{"date": d.isoformat(), "name": HOLIDAYS[d][0],
             "demand_multiplier": HOLIDAYS[d][1]} for d in sorted(HOLIDAYS)]
write_csv("holidays.csv", hol_rows, ["date","name","demand_multiplier"])

# vehicles.csv
veh_rows = [{"vehicle_type": v[0], "capacity_litres": v[1],
             "purchase_cost_inr": v[2], "fuel_cost_per_km": v[3],
             "co2_g_per_km": v[4], "crew_size": v[5]} for v in vehicles]
write_csv("vehicles.csv", veh_rows,
          ["vehicle_type","capacity_litres","purchase_cost_inr",
           "fuel_cost_per_km","co2_g_per_km","crew_size"])

# anomaly answer key (A17) -> JSON, kept separate so it's clearly a "key"
with open(os.path.join(OUT, "anomaly_key.json"), "w") as f:
    json.dump({
        "note": "Ground-truth answer key for A17 (surge-alarm). Do NOT give to students who must find these themselves; for faculty grading.",
        "events": [
            {"date": surge_day.isoformat(), "type": "real_surge",
             "cause": "heatwave dust event; demand ~2.3x normal"},
            {"date": glitch_day.isoformat(), "type": "data_glitch",
             "cause": "double-logged bookings (~40% duplicated rows)"},
        ]
    }, f, indent=2)

# a small daily-demand summary (handy for A02/A17 sanity checks) -> daily_summary.csv
daily = defaultdict(lambda: {"bookings":0,"revenue":0.0,"noshows":0})
for b in bookings:
    # raw booking count includes duplicates on purpose — that inflated count
    # is exactly the signal A17 must learn to distinguish from a real surge.
    daily[b["date"]]["bookings"] += 1
    if b["status"] == "no_show":
        daily[b["date"]]["noshows"] += 1
    elif b["status"] == "completed":
        tp = b["total_price"]
        daily[b["date"]]["revenue"] += float(tp) if tp not in ("", None) else 0.0
daily_rows = []
for d in ALL_DATES:
    k = d.isoformat()
    row = daily[k]
    temp, rain, cond = WEATHER[d]
    daily_rows.append({
        "date": k, "total_bookings": row["bookings"],
        "no_shows": row["noshows"], "revenue": round(row["revenue"],0),
        "temp_c": temp, "rain_mm": rain, "condition": cond,
        "is_holiday": int(d in HOLIDAYS),
        "dow": d.strftime("%a"),
    })
write_csv("daily_summary.csv", daily_rows,
          ["date","total_bookings","no_shows","revenue","temp_c","rain_mm",
           "condition","is_holiday","dow"])

print("Files written to", OUT)
for fn in sorted(os.listdir(OUT)):
    sz = os.path.getsize(os.path.join(OUT, fn))
    print(f"  {fn:24s} {sz:>10,} bytes")
