"""Loads the fictional sample schedule, the port list and the FAQ."""
import csv
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


@lru_cache(maxsize=None)
def meta():
    return json.loads((DATA / "sample_meta.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def rows():
    with open(DATA / "sample_schedule.csv", encoding="utf-8", newline="") as f:
        out = list(csv.DictReader(f))
    for r in out:
        r["transit_days"] = int(r["transit_days"])
    return out


@lru_cache(maxsize=None)
def ports():
    return json.loads((DATA / "ports.json").read_text(encoding="utf-8"))["ports"]


@lru_cache(maxsize=None)
def port_names():
    return {p["code"]: p["name"] for p in ports()}


@lru_cache(maxsize=None)
def aliases():
    """alias (lower case) -> code, longest alias first."""
    pairs = [(a, p["code"]) for p in ports() for a in p["aliases"]]
    return sorted(pairs, key=lambda x: -len(x[0]))


@lru_cache(maxsize=None)
def faq():
    return json.loads((DATA / "faq.json").read_text(encoding="utf-8"))["entries"]


@lru_cache(maxsize=None)
def carriers():
    return sorted({r["carrier"] for r in rows()})
