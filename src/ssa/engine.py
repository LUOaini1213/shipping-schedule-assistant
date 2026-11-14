"""Retrieve rows for a structured query, compose a cited answer, or refuse."""
from datetime import date

from . import data, guard
from .parser import parse

REFUSALS = {
    "out_of_scope": "I can only answer questions about sailings in the sample schedule "
                    "(dates, transit time, cut-offs) and general booking and documentation "
                    "questions. I cannot help with rates, tracking, customs duty or making a booking.",
    "unknown_port": "A port in your question is not in the sample port list, so I cannot "
                    "look up sailings for it.",
    "missing_info": "Please give both the origin port and the destination port, or a sailing ID, "
                    "so I can look this up.",
    "no_data": "The sample schedule has no sailing matching that request, and I will not guess one.",
    "guard_blocked": "I could not produce an answer that is fully backed by the retrieved "
                     "records, so I am not answering.",
}
FIELD_LABEL = {"cy_cutoff": "CY cut-off", "doc_cutoff": "Documentation cut-off",
               "vgm_cutoff": "VGM cut-off"}
SCHEDULE_OPS = {"list", "count", "transit", "fastest", "earliest_arrival", "next", "cutoff", "detail"}


def retrieve(part, as_of):
    """Rows matching the filters, then reduced according to the op."""
    rows = data.rows()
    if part.get("sailing_id"):
        return [r for r in rows if r["sailing_id"] == part["sailing_id"]]
    lo = max(part.get("etd_from") or as_of, as_of)
    hit = [r for r in rows
           if r["origin_code"] == part["origin"] and r["dest_code"] == part["dest"]
           and lo <= r["etd"] <= (part.get("etd_to") or "9999")
           and r["eta"] <= (part.get("eta_to") or "9999")
           and (not part.get("direct") or r["routing"] == "direct")
           and (not part.get("carrier") or r["carrier"] == part["carrier"])]
    op = part["op"]
    if hit and op == "fastest":
        best = min(r["transit_days"] for r in hit)
        hit = [r for r in hit if r["transit_days"] == best]
    elif hit and op == "earliest_arrival":
        best = min(r["eta"] for r in hit)
        hit = [r for r in hit if r["eta"] == best]
    elif hit and op in ("next", "cutoff"):
        best = min(r["etd"] for r in hit)
        hit = [r for r in hit if r["etd"] == best]
    return sorted(hit, key=lambda r: r["sailing_id"])


def _port(code):
    return f"{data.port_names()[code]} ({code})"


def row_line(r):
    routing = "direct" if r["routing"] == "direct" else f"via {_port(r['via_code'])}"
    return (f"{r['sailing_id']}: {r['carrier']}, {r['vessel']} {r['voyage']} (service {r['service']}), "
            f"ETD {r['etd']} {_port(r['origin_code'])} to ETA {r['eta']} {_port(r['dest_code'])}, "
            f"{r['transit_days']} days, {routing}; CY cut-off {r['cy_cutoff']}, "
            f"documentation cut-off {r['doc_cutoff']}, VGM cut-off {r['vgm_cutoff']} [{r['sailing_id']}]")


def compose(part, rows):
    op = part["op"]
    cites = " ".join(f"[{r['sailing_id']}]" for r in rows)
    if op == "count":
        return f"The sample schedule has {len(rows)} matching sailing(s) {cites}", len(rows)
    if op == "transit":
        days = [r["transit_days"] for r in rows]
        span = f"{min(days)} days" if min(days) == max(days) else f"{min(days)} to {max(days)} days"
        return (f"Transit time is {span} across the {len(rows)} matching sailing(s) "
                f"in the sample schedule {cites}"), [min(days), max(days)]
    if op == "cutoff":
        f = part["field"]
        lines = [f"{FIELD_LABEL[f]} for {r['sailing_id']} ({r['carrier']}, {r['vessel']} {r['voyage']}, "
                 f"ETD {r['etd']} {_port(r['origin_code'])} to {_port(r['dest_code'])}) is {r[f]}, "
                 f"local time at the origin port [{r['sailing_id']}]" for r in rows]
        return "\n".join(lines), sorted(r[f] for r in rows)
    head = {"list": "Sailings in the sample schedule matching your request:",
            "fastest": "Shortest transit among matching sailings in the sample schedule:",
            "earliest_arrival": "Earliest arrival among matching sailings in the sample schedule:",
            "next": "Next departure in the sample schedule:",
            "detail": "Sailing detail from the sample schedule:"}[op]
    return "\n".join([head] + [row_line(r) for r in rows]), None


def _refusal(reason, query=None):
    return {"op": "refuse", "reason": reason, "text": REFUSALS[reason], "ids": [],
            "value": None, "evidence": {}, "query": query}


def run_part(part, as_of):
    op = part.get("op")
    if op == "refuse":
        return _refusal(part["reason"], part)
    if op == "faq":
        entry = next((e for e in data.faq() if e["id"] == part.get("faq_id")), None)
        if entry is None:
            return _refusal("out_of_scope", part)
        text, value, evidence = f"{entry['answer']} [{entry['id']}]", None, {entry["id"]: entry}
    elif op in SCHEDULE_OPS:
        rows = retrieve(part, as_of)
        if not rows:
            return _refusal("no_data", part)
        text, value = compose(part, rows)
        evidence = {r["sailing_id"]: r for r in rows}
    else:
        return _refusal("out_of_scope", part)
    if guard.check(text, evidence):
        return _refusal("guard_blocked", part)
    return {"op": op, "ids": sorted(evidence), "value": value, "text": text,
            "evidence": evidence, "query": part}


def answer(question, as_of=None, parts=None, parser_name="rule"):
    """Answer a question. `parts` lets a caller supply an already-parsed query
    (used by the optional LLM parser); otherwise the rule parser is used."""
    as_of = as_of or data.meta()["as_of"]
    if parts is None:
        parts = parse(question, date.fromisoformat(as_of))
    results = [run_part(p, as_of) for p in parts]
    return {
        "question": question,
        "parser": parser_name,
        "as_of": as_of,
        "parts": results,
        "text": "\n\n".join(r["text"] for r in results),
        "refused": all(r["op"] == "refuse" for r in results),
        "notice": f"Fictional sample data, as of {as_of}. Not a real carrier schedule; "
                  "confirm everything with your carrier.",
    }


def key(result):
    """The part of a result that the evaluation compares with the oracle."""
    out = []
    for p in result["parts"]:
        if p["op"] == "refuse":
            out.append({"op": "refuse", "reason": p["reason"]})
        else:
            out.append({"op": p["op"], "ids": p["ids"], "value": p["value"]})
    return out
