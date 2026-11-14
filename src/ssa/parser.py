"""Rule parser: question text -> list of structured query parts.

A part is a plain dict using the same vocabulary as the LLM parser:
  {"op": "list|count|transit|fastest|earliest_arrival|next|cutoff|detail",
   "origin", "dest", "sailing_id", "etd_from", "etd_to", "eta_to",
   "direct", "carrier", "field"}
  {"op": "faq", "faq_id": "FAQ-nn"}
  {"op": "refuse", "reason": "out_of_scope|unknown_port|missing_info|no_data"}
The parser never writes answer text.
"""
import re
from datetime import date, timedelta

from . import data

MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
          "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
          "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
          "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "seven": 7, "ten": 10,
                "fourteen": 14, "thirty": 30}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))

OUT_OF_SCOPE = re.compile(
    r"\b(rates?|prices?|pricing|costs?|quote|quotation|how much|freight charge|surcharges?"
    r"|track|tracking|where is my|weather|duty|duties|tariff|tax|poem|joke"
    r"|book (a|it|this|me)\b|book .* for me|place a booking for)\b")
SCHEDULE_WORDS = re.compile(
    r"\b(sailings?|schedules?|vessels?|depart\w*|cut-?offs?|cut off|transit|voyage|etd|eta|arriv\w*)\b")
CUTOFF = re.compile(r"cut-?off|cut off|closing|deadline|by when|latest time|gate[- ]in")
DOC_FIELD = re.compile(r"\bdoc\b|\bdocs\b|documentation|\bsi\b|shipping instruction")
COUNT = re.compile(r"how many (sailings|departures|vessels|options)|\bcount\b|number of sailings")
TRANSIT = re.compile(r"transit|how long|how many days|duration")
FASTEST = re.compile(r"fastest|quickest|shortest")
EARLIEST_ARRIVAL = re.compile(
    r"arrives? (the )?(earliest|first|soonest)|earliest arrival|gets? there first"
    r"|arrive first|soonest arrival")
NEXT = re.compile(r"(next|earliest|first|soonest) (\w+ )?(sailing|departure|vessel)")
DIRECT = re.compile(r"\bdirect\b|non-?stop|no transshipment|without transshipment")
SAILING_ID = re.compile(r"\bdl-(\d{4})\b")
ORIGIN_CUE = re.compile(r"(from|ex|leave|leaves|leaving|departing|depart|out of)\s+$")
DEST_CUE = re.compile(r"(to|into|for|->|→|arriving|arrive in|reach)\s+$")
UNKNOWN_PORT = re.compile(r"\b(?:from|to|into|ex)\s+([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)")
# FAQ topics that may be added to a schedule question as a second part
COMPOUND_FAQ = {"FAQ-01", "FAQ-02", "FAQ-05", "FAQ-06", "FAQ-07", "FAQ-08", "FAQ-10", "FAQ-12"}


def _iso(d):
    return d.isoformat()


def find_ports(text):
    """Return [(start, end, code)] for known port mentions, left to right."""
    found, taken = [], [False] * len(text)
    for alias, code in data.aliases():
        for m in re.finditer(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            found.append((m.start(), m.end(), code))
    return sorted(found)


def assign_ports(text, mentions):
    origin = dest = None
    loose = []
    for start, _end, code in mentions:
        before = text[max(0, start - 12):start]
        if ORIGIN_CUE.search(before) and origin is None:
            origin = code
        elif DEST_CUE.search(before) and dest is None:
            dest = code
        else:
            loose.append(code)
    for code in loose:
        if origin is None:
            origin = code
        elif dest is None:
            dest = code
    return origin, dest


def has_unknown_port(raw):
    known = [a for a, _ in data.aliases()]
    for m in UNKNOWN_PORT.finditer(raw):
        cand = m.group(1).lower()
        first = cand.split()[0]
        if first in MONTHS or first in ("demo", "dl", "the", "a", "my", "book", "ship"):
            continue
        if any(cand == a or cand.startswith(a + " ") for a in known):
            continue
        return True
    return False


def _explicit_dates(text, year):
    """[(start, end, date)] for ISO dates and day-month forms."""
    out = []
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            out.append((m.start(), m.end(), date(int(m[1]), int(m[2]), int(m[3]))))
        except ValueError:
            pass
    pats = [r"\b(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?P<m>%s)\b(?:\s+(?P<y>\d{4}))?" % _MONTH_RE,
            r"\b(?P<m>%s)\s+(?P<d>\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(?P<y>\d{4}))?" % _MONTH_RE]
    for pat in pats:
        for m in re.finditer(pat, text):
            if any(s <= m.start() < e for s, e, _ in out):
                continue
            try:
                out.append((m.start(), m.end(),
                            date(int(m["y"] or year), MONTHS[m["m"]], int(m["d"]))))
            except ValueError:
                pass
    return sorted(out)


def parse_dates(text, as_of):
    """Return {"etd_from", "etd_to", "eta_to"} (ISO strings, only keys found)."""
    out = {}
    found = _explicit_dates(text, as_of.year)
    masked = list(text)
    for s, e, _ in found:
        masked[s:e] = " " * (e - s)
    masked = "".join(masked)

    if len(found) >= 2 and re.search(r"between|from", text[:found[1][0]]):
        out["etd_from"], out["etd_to"] = _iso(found[0][2]), _iso(found[1][2])
    elif found:
        s, _e, d = found[0]
        before = text[max(0, s - 22):s]
        if re.search(r"(arriv\w*|eta|get there|reach\w*)\s+(by|before|on or before)\s+$", before):
            out["eta_to"] = _iso(d - timedelta(days=1) if before.rstrip().endswith("before")
                                 and "on or before" not in before else d)
        elif re.search(r"(after|from|since|on or after)\s+$", before):
            out["etd_from"] = _iso(d)
        elif re.search(r"on or before\s+$|\b(by|until|till)\s+$", before):
            out["etd_to"] = _iso(d)
        elif re.search(r"before\s+$", before):
            out["etd_to"] = _iso(d - timedelta(days=1))
        else:
            out["etd_from"] = out["etd_to"] = _iso(d)
        return out
    if out:
        return out

    monday = as_of - timedelta(days=as_of.weekday())
    if "next week" in masked:
        out["etd_from"], out["etd_to"] = _iso(monday + timedelta(days=7)), _iso(monday + timedelta(days=13))
    elif "this week" in masked:
        out["etd_from"], out["etd_to"] = _iso(monday), _iso(monday + timedelta(days=6))
    elif "tomorrow" in masked:
        out["etd_from"] = out["etd_to"] = _iso(as_of + timedelta(days=1))
    elif re.search(r"\btoday\b", masked):
        out["etd_from"] = out["etd_to"] = _iso(as_of)
    else:
        m = re.search(r"next (\d+|%s) (days?|weeks?)" % "|".join(NUMBER_WORDS), masked)
        if m:
            n = int(m[1]) if m[1].isdigit() else NUMBER_WORDS[m[1]]
            n *= 7 if m[2].startswith("week") else 1
            out["etd_from"], out["etd_to"] = _iso(as_of), _iso(as_of + timedelta(days=n))
        else:
            m = re.search(r"\b(%s)\b" % _MONTH_RE, masked)
            if m and not (m[1] in ("may", "mar") and not re.search(r"\b(in|during)\s+" + m[1], masked)):
                mon = MONTHS[m[1]]
                first = date(as_of.year, mon, 1)
                nxt = date(as_of.year + (mon == 12), mon % 12 + 1, 1)
                out["etd_from"], out["etd_to"] = _iso(first), _iso(nxt - timedelta(days=1))
    return out


def match_faq(text):
    """Best FAQ entry by keyword hits; ties broken by the longest keyword hit."""
    best = None
    for e in data.faq():
        hits = [k for k in e["keywords"] if k in text]
        if hits:
            score = (len(hits), max(len(k) for k in hits))
            if best is None or score > best[0]:
                best = (score, e["id"])
    return best[1] if best else None


def match_carrier(text):
    for c in data.carriers():
        if c.lower() in text or re.search(r"\b" + c.split()[-1].lower() + r"\b", text):
            return c
    return None


def parse(question, as_of=None):
    as_of = as_of or date.fromisoformat(data.meta()["as_of"])
    raw = question.strip()
    text = raw.lower()
    if not text:
        return [{"op": "refuse", "reason": "out_of_scope"}]
    if OUT_OF_SCOPE.search(text):
        return [{"op": "refuse", "reason": "out_of_scope"}]

    faq_id = match_faq(text)
    sid = SAILING_ID.search(text)
    mentions = find_ports(text)
    is_cutoff = bool(CUTOFF.search(text))
    field = ("vgm_cutoff" if "vgm" in text else
             "doc_cutoff" if DOC_FIELD.search(text) else "cy_cutoff")

    if sid:
        part = {"op": "cutoff" if is_cutoff else "detail", "sailing_id": "DL-" + sid[1]}
        if is_cutoff:
            part["field"] = field
        return [part]

    if has_unknown_port(raw):
        return [{"op": "refuse", "reason": "unknown_port"}]

    origin, dest = assign_ports(text, mentions)
    if origin is None or dest is None:
        if faq_id and not (mentions and SCHEDULE_WORDS.search(text) and faq_id not in COMPOUND_FAQ):
            return [{"op": "faq", "faq_id": faq_id}]
        if mentions or SCHEDULE_WORDS.search(text):
            return [{"op": "refuse", "reason": "missing_info"}]
        return [{"op": "refuse", "reason": "out_of_scope"}]

    part = {"origin": origin, "dest": dest}
    part.update(parse_dates(text, as_of))
    if DIRECT.search(text):
        part["direct"] = True
    carrier = match_carrier(text)
    if carrier:
        part["carrier"] = carrier
    if is_cutoff:
        part["op"], part["field"] = "cutoff", field
    elif COUNT.search(text):
        part["op"] = "count"
    elif TRANSIT.search(text):
        part["op"] = "transit"
    elif FASTEST.search(text):
        part["op"] = "fastest"
    elif EARLIEST_ARRIVAL.search(text):
        part["op"] = "earliest_arrival"
    elif NEXT.search(text):
        part["op"] = "next"
    else:
        part["op"] = "list"
    parts = [part]
    if faq_id in COMPOUND_FAQ and part["op"] != "cutoff":
        parts.append({"op": "faq", "faq_id": faq_id})
    return parts
