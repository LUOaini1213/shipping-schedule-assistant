"""Grounding guard: every date, time, number and port in an answer line must
come from the records that line cites.

A line cites records with [DL-nnnn] or [FAQ-nn]. The only derived number that
is allowed is the count of citations on the line.
"""
import re

from . import data
from .parser import find_ports

CITATION = re.compile(r"\[(DL-\d{4}|FAQ-\d{2})\]")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
CLOCK = re.compile(r"\b\d{2}:\d{2}\b")
NUMBER = re.compile(r"\d+")


def tokens(text):
    """Split a string into (dates, times, other numbers)."""
    dates = set(ISO_DATE.findall(text))
    text = ISO_DATE.sub(" ", text)
    times = set(CLOCK.findall(text))
    text = CLOCK.sub(" ", text)
    return dates, times, set(NUMBER.findall(text))


def record_text(record):
    return " ".join(str(v) for k, v in record.items() if k != "keywords")


def record_ports(record):
    if "origin_code" in record:
        return {record["origin_code"], record["dest_code"], record["via_code"]} - {""}
    return {c for _s, _e, c in find_ports(record_text(record).lower())}


def check(text, evidence):
    """Return a list of violations; empty means the text is grounded.

    evidence: {citation id: record dict} for the records that were retrieved.
    """
    problems = []
    for line in text.splitlines():
        cited = CITATION.findall(line)
        body = CITATION.sub(" ", line)
        missing = [c for c in cited if c not in evidence]
        if missing:
            problems.append(f"cites a record that was not retrieved: {missing[0]}")
            continue
        ev_text = " ".join(record_text(evidence[c]) for c in cited)
        ev_dates, ev_times, ev_nums = tokens(ev_text)
        ev_ports = set().union(*[record_ports(evidence[c]) for c in cited]) if cited else set()
        dates, times, nums = tokens(body)
        for d in sorted(dates - ev_dates):
            problems.append(f"date {d} not in cited records")
        for t in sorted(times - ev_times):
            problems.append(f"time {t} not in cited records")
        for n in sorted(nums - ev_nums):
            if int(n) != len(cited) or not cited:
                problems.append(f"number {n} not in cited records")
        for _s, _e, code in find_ports(body.lower()):
            if code not in ev_ports:
                problems.append(f"port {data.port_names()[code]} not in cited records")
    return problems
