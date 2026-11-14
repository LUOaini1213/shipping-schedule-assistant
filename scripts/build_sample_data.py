"""Author the FICTIONAL sample schedule (data/sample_schedule.csv).

Nothing here is a real carrier schedule. Carriers, vessels, voyages, dates,
transit times and cut-offs are invented by a seeded generator; only the port
names and UN/LOCODEs are real. Re-running reproduces the committed file.
"""
import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 11, 16)          # a Monday; "today" for the demo
WEEKS = 6                           # sailings from AS_OF for six weeks
SEED = 20261114

# origin, dest, carrier, service, weekday (0=Mon), base transit days, via
LANES = [
    ("SGSIN", "NLRTM", "Demo Line Alfa", "AE1", 1, 24, ""),
    ("SGSIN", "NLRTM", "Demo Line Bravo", "EU2", 4, 29, "LKCMB"),
    ("SGSIN", "DEHAM", "Demo Line Alfa", "AE1", 1, 27, ""),
    ("SGSIN", "USLAX", "Demo Line Charlie", "TP3", 3, 23, "CNSHA"),
    ("SGSIN", "AEJEA", "Demo Line Bravo", "ME1", 0, 11, "MYPKG"),
    ("SGSIN", "AEJEA", "Demo Line Alfa", "ME4", 4, 10, ""),
    ("SGSIN", "LKCMB", "Demo Line Bravo", "EU2", 4, 5, ""),
    ("SGSIN", "CNSHA", "Demo Line Alfa", "IA5", 2, 6, ""),
    ("SGSIN", "CNSHA", "Demo Line Bravo", "IA1", 5, 7, "HKHKG"),
    ("SGSIN", "HKHKG", "Demo Line Charlie", "IA7", 0, 5, ""),
    ("SGSIN", "MYPKG", "Demo Line Alfa", "FD1", 1, 1, ""),
    ("SGSIN", "MYPKG", "Demo Line Alfa", "FD1", 4, 1, ""),
    ("CNSHA", "USLAX", "Demo Line Alfa", "TP1", 2, 14, ""),
    ("CNSHA", "USLAX", "Demo Line Charlie", "TP3", 5, 13, ""),
    ("CNSHA", "NLRTM", "Demo Line Bravo", "EU2", 0, 32, "SGSIN"),
    ("CNSHA", "SGSIN", "Demo Line Bravo", "IA1", 6, 6, ""),
    ("CNSHA", "SGSIN", "Demo Line Alfa", "IA5", 3, 7, "CNYTN"),
    ("CNNGB", "USLAX", "Demo Line Alfa", "TP1", 0, 16, "CNSHA"),
    ("CNNGB", "SGSIN", "Demo Line Charlie", "IA7", 1, 8, "HKHKG"),
    ("CNYTN", "NLRTM", "Demo Line Alfa", "AE1", 5, 26, "SGSIN"),
    ("CNYTN", "SGSIN", "Demo Line Alfa", "IA5", 6, 4, ""),
    ("HKHKG", "SGSIN", "Demo Line Charlie", "IA7", 4, 4, ""),
    ("KRPUS", "USLAX", "Demo Line Charlie", "TP3", 0, 11, ""),
    ("KRPUS", "SGSIN", "Demo Line Bravo", "IA1", 3, 9, "CNSHA"),
    ("MYPKG", "AEJEA", "Demo Line Bravo", "ME1", 2, 9, ""),
    ("LKCMB", "NLRTM", "Demo Line Bravo", "EU2", 2, 20, ""),
    ("AEJEA", "NLRTM", "Demo Line Alfa", "ME4", 6, 18, ""),
]
VESSELS = ["DEMO ALBATROSS", "DEMO BANYAN", "DEMO CORMORANT", "DEMO DUGONG",
           "DEMO EGRET", "DEMO FRANGIPANI", "DEMO GIBBON", "DEMO HORNBILL",
           "DEMO IXORA", "DEMO JACANA", "DEMO KINGFISHER", "DEMO LANTANA"]
FIELDS = ["sailing_id", "carrier", "service", "vessel", "voyage",
          "origin_code", "dest_code", "etd", "eta", "transit_days",
          "routing", "via_code", "cy_cutoff", "doc_cutoff", "vgm_cutoff"]


def build():
    rng = random.Random(SEED)
    rows = []
    for (o, d, carrier, service, wd, base, via) in LANES:
        for week in range(WEEKS):
            if rng.random() < 0.12:          # an invented "blank sailing"
                continue
            etd = AS_OF + timedelta(days=7 * week + wd)
            transit = base + rng.choice([0, 0, 0, 1, 2])
            eta = etd + timedelta(days=transit)
            cy = datetime(etd.year, etd.month, etd.day, rng.choice([12, 16, 18])) \
                - timedelta(days=rng.choice([1, 2]))
            doc = datetime(etd.year, etd.month, etd.day, rng.choice([10, 12, 17])) \
                - timedelta(days=rng.choice([2, 3]))
            vgm = cy - timedelta(hours=rng.choice([0, 4, 6]))
            rows.append({
                "carrier": carrier, "service": service,
                "vessel": rng.choice(VESSELS),
                "voyage": f"{rng.randint(601, 699)}{rng.choice('EW')}",
                "origin_code": o, "dest_code": d,
                "etd": etd.isoformat(), "eta": eta.isoformat(),
                "transit_days": transit,
                "routing": "transshipment" if via else "direct", "via_code": via,
                "cy_cutoff": cy.strftime("%Y-%m-%d %H:%M"),
                "doc_cutoff": doc.strftime("%Y-%m-%d %H:%M"),
                "vgm_cutoff": vgm.strftime("%Y-%m-%d %H:%M"),
            })
    rows.sort(key=lambda r: (r["etd"], r["origin_code"], r["dest_code"], r["carrier"]))
    for i, r in enumerate(rows, 1):
        r["sailing_id"] = f"DL-{i:04d}"
    return rows


def main():
    rows = build()
    with open(ROOT / "data" / "sample_schedule.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    meta = {
        "label": "FICTIONAL SAMPLE DATA - not a real carrier schedule",
        "as_of": AS_OF.isoformat(),
        "first_etd": rows[0]["etd"], "last_etd": rows[-1]["etd"],
        "rows": len(rows), "seed": SEED,
        "times": "cut-offs are invented and expressed as local time at the origin port",
    }
    (ROOT / "data" / "sample_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
