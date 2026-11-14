"""Optional parser backed by a local model served by Ollama.

The model only fills in the structured query. It never writes answer text:
its output is validated against the port list, FAQ ids and field names, and
anything invalid falls back to the rule parser. Tests and CI do not need it.
"""
import json
import re
import urllib.request

from . import data
from .parser import parse

OPS = {"list", "count", "transit", "fastest", "earliest_arrival", "next", "cutoff", "detail",
       "faq", "refuse"}
REASONS = {"out_of_scope", "unknown_port", "missing_info", "no_data"}
FIELDS = {"cy_cutoff", "doc_cutoff", "vgm_cutoff"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAILING = re.compile(r"^DL-\d{4}$")


def build_prompt(question, as_of):
    from datetime import date, timedelta
    today = date.fromisoformat(as_of)
    monday = today - timedelta(days=today.weekday())
    nw0, nw1 = (monday + timedelta(days=7)).isoformat(), (monday + timedelta(days=13)).isoformat()
    ports = ", ".join(f"{p['name']}={p['code']}" for p in data.ports())
    topics = "; ".join(f"{e['id']}={e['topic']}" for e in data.faq())
    return f"""You convert a shipper's question into a JSON query. Today is {as_of}.
Return only JSON: {{"parts": [part, ...]}} with one part, or two parts when the question asks for sailings and also a booking/documents question.
Schedule part keys: "op" (list, count, transit, fastest, earliest_arrival, next, cutoff, detail), "origin" and "dest" (port codes), or "sailing_id" (DL-nnnn) for detail/cutoff; optional "etd_from", "etd_to", "eta_to" (YYYY-MM-DD, inclusive), "direct" (true), "carrier" ({", ".join(data.carriers())}); cutoff needs "field" (cy_cutoff, doc_cutoff, vgm_cutoff).
FAQ part: {{"op": "faq", "faq_id": "FAQ-nn"}}. Topics: {topics}.
Refusal part: {{"op": "refuse", "reason": R}}, R = out_of_scope (rates, tracking, customs duty, making a booking, anything else), unknown_port (a port not in the list), missing_info (origin or destination missing and no sailing id).
Known ports: {ports}.
Dates: this week = Monday to Sunday containing today; next week = the following Monday to Sunday; next N days = today to today+N; a month name = that whole month; "before X" = etd_to the day before X; "arriving by X" = eta_to X. Omit keys you do not need.
Examples (today {as_of}):
Q: Which sailings go from Shanghai to Busan next week?
A: {{"parts": [{{"op": "list", "origin": "CNSHA", "dest": "KRPUS", "etd_from": "{nw0}", "etd_to": "{nw1}"}}]}}
Q: fastest way hong kong to jebel ali, and how do I cancel a booking?
A: {{"parts": [{{"op": "fastest", "origin": "HKHKG", "dest": "AEJEA"}}, {{"op": "faq", "faq_id": "FAQ-06"}}]}}
Q: doc cut-off for DL-0001?
A: {{"parts": [{{"op": "cutoff", "sailing_id": "DL-0001", "field": "doc_cutoff"}}]}}
Q: What is VGM?
A: {{"parts": [{{"op": "faq", "faq_id": "FAQ-03"}}]}}
Q: How much is the freight to Hamburg?
A: {{"parts": [{{"op": "refuse", "reason": "out_of_scope"}}]}}
Q: {question}
A:"""


def validate(parts):
    """Return cleaned parts, or None if anything is not allowed."""
    if not isinstance(parts, list) or not 1 <= len(parts) <= 2:
        return None
    codes = set(data.port_names())
    faq_ids = {e["id"] for e in data.faq()}
    out = []
    for p in parts:
        if not isinstance(p, dict) or p.get("op") not in OPS:
            return None
        op = p["op"]
        if op == "refuse":
            if p.get("reason") not in REASONS:
                return None
            out.append({"op": "refuse", "reason": p["reason"]})
        elif op == "faq":
            if p.get("faq_id") not in faq_ids:
                return None
            out.append({"op": "faq", "faq_id": p["faq_id"]})
        else:
            clean = {"op": op}
            if p.get("sailing_id"):
                if not SAILING.match(str(p["sailing_id"])):
                    return None
                clean["sailing_id"] = p["sailing_id"]
            elif p.get("origin") in codes and p.get("dest") in codes:
                clean["origin"], clean["dest"] = p["origin"], p["dest"]
            else:
                return None
            for k in ("etd_from", "etd_to", "eta_to"):
                if p.get(k):
                    if not ISO.match(str(p[k])):
                        return None
                    clean[k] = p[k]
            if p.get("direct") is True:
                clean["direct"] = True
            if p.get("carrier"):
                if p["carrier"] not in data.carriers():
                    return None
                clean["carrier"] = p["carrier"]
            if op == "cutoff":
                if p.get("field") not in FIELDS:
                    return None
                clean["field"] = p["field"]
            if op == "detail" and "sailing_id" not in clean:
                return None
            out.append(clean)
    return out


def parse_with_ollama(question, as_of, model, host="http://127.0.0.1:11434", timeout=120):
    """Return (parts, parser_name). Falls back to the rule parser on any failure."""
    from datetime import date
    try:
        body = json.dumps({"model": model, "prompt": build_prompt(question, as_of),
                           "format": "json", "stream": False,
                           "options": {"temperature": 0}}).encode("utf-8")
        req = urllib.request.Request(host + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))["response"]
        parts = validate(json.loads(raw).get("parts"))
    except Exception:
        parts = None
    if parts is None:
        return parse(question, date.fromisoformat(as_of)), "rule-fallback"
    return parts, "llm:" + model
