"""Independent oracle: turns the hand-written gold specs in questions.jsonl
into expected answers by filtering the CSV directly.

Deliberately imports nothing from src/ssa, so a bug in the product parser or
retrieval cannot leak into the expected answers. The natural-language reading
of each question (ports, dates, intent) is the hand-labelled part.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AS_OF = json.loads((ROOT / "data" / "sample_meta.json").read_text(encoding="utf-8"))["as_of"]


def load_rows():
    with open(ROOT / "data" / "sample_schedule.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def expected_part(spec, rows):
    op = spec["op"]
    if op == "refuse":
        return {"op": "refuse", "reason": spec["reason"]}
    if op == "faq":
        return {"op": "faq", "ids": [spec["faq"]], "value": None}
    if "id" in spec:
        hit = [r for r in rows if r["sailing_id"] == spec["id"]]
    else:
        lo = max(spec.get("etd_from", AS_OF), AS_OF)
        hit = []
        for r in rows:
            if r["origin_code"] != spec["o"] or r["dest_code"] != spec["d"]:
                continue
            if r["etd"] < lo or r["etd"] > spec.get("etd_to", "9999"):
                continue
            if r["eta"] > spec.get("eta_to", "9999"):
                continue
            if spec.get("direct") and r["routing"] != "direct":
                continue
            if "carrier" in spec and r["carrier"] != spec["carrier"]:
                continue
            hit.append(r)
    if not hit:
        return {"op": "refuse", "reason": "no_data"}
    value = None
    if op == "transit":
        days = [int(r["transit_days"]) for r in hit]
        value = [min(days), max(days)]
    elif op == "count":
        value = len(hit)
    elif op == "fastest":
        best = min(int(r["transit_days"]) for r in hit)
        hit = [r for r in hit if int(r["transit_days"]) == best]
    elif op == "earliest_arrival":
        best = min(r["eta"] for r in hit)
        hit = [r for r in hit if r["eta"] == best]
    elif op in ("next", "cutoff"):
        best = min(r["etd"] for r in hit)
        hit = [r for r in hit if r["etd"] == best]
        if op == "cutoff":
            value = sorted(r[spec["field"]] for r in hit)
    return {"op": op, "ids": sorted(r["sailing_id"] for r in hit), "value": value}


def build():
    rows = load_rows()
    out = {}
    for line in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        out[q["id"]] = [expected_part(s, rows) for s in q["gold"]]
    return out


def main():
    out = build()
    (HERE / "expected.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(len(out), "expected answers written")


if __name__ == "__main__":
    main()
