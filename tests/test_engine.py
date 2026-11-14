import re

import pytest

from ssa import data, engine, guard, llm


def test_list_answer_is_cited_and_grounded():
    res = engine.answer("Which sailings go from Singapore to Rotterdam next week?")
    part = res["parts"][0]
    assert part["ids"] == ["DL-0034", "DL-0045"]
    assert "[DL-0034]" in part["text"] and "[DL-0045]" in part["text"]
    assert guard.check(part["text"], part["evidence"]) == []
    assert "Fictional sample data" in res["notice"] and not res["refused"]


def test_past_departures_are_excluded():
    q = "Sailings from Singapore to Rotterdam"
    all_ids = engine.answer(q)["parts"][0]["ids"]
    later = engine.answer(q, as_of="2026-12-10")["parts"][0]["ids"]
    assert "DL-0020" in all_ids and later == ["DL-0095", "DL-0109", "DL-0120", "DL-0134", "DL-0145"]


def test_filters_change_the_rows():
    base = {"op": "list", "origin": "SGSIN", "dest": "AEJEA"}
    rows = engine.retrieve(base, "2026-11-16")
    direct = engine.retrieve(dict(base, direct=True), "2026-11-16")
    bravo = engine.retrieve(dict(base, carrier="Demo Line Bravo"), "2026-11-16")
    by_eta = engine.retrieve(dict(base, eta_to="2026-11-30"), "2026-11-16")
    assert len(rows) == 11 and len(direct) == 5 and len(bravo) == 6
    assert {r["routing"] for r in direct} == {"direct"}
    assert [r["sailing_id"] for r in by_eta] == ["DL-0004", "DL-0017"]


def test_superlatives_keep_all_ties():
    part = {"origin": "CNYTN", "dest": "SGSIN"}
    assert [r["sailing_id"] for r in engine.retrieve(dict(part, op="fastest"), "2026-11-16")] == [
        "DL-0051", "DL-0075", "DL-0125", "DL-0151"]
    assert [r["sailing_id"] for r in engine.retrieve(dict(part, op="next"), "2026-11-16")] == ["DL-0026"]
    arr = engine.retrieve({"op": "earliest_arrival", "origin": "SGSIN", "dest": "NLRTM"}, "2026-11-16")
    assert [r["sailing_id"] for r in arr] == ["DL-0020", "DL-0034"]


def test_values():
    assert engine.answer("transit time from Singapore to Hamburg")["parts"][0]["value"] == [27, 28]
    assert engine.answer("how many sailings from Port Klang to Dubai")["parts"][0]["value"] == 6
    cut = engine.answer("VGM cut-off for DL-0059")["parts"][0]
    assert cut["value"] == ["2026-11-30 14:00"] and "2026-11-30 14:00" in cut["text"]
    assert "VGM cut-off" in cut["text"]
    same = engine.answer("How many days from Yantian to Rotterdam?")["parts"][0]
    assert same["value"] == [26, 26] and "26 days" in same["text"] and " to 26 " not in same["text"]


def test_transshipment_port_is_named():
    text = engine.answer("details of DL-0045")["text"]
    assert "via Colombo (LKCMB)" in text
    assert "direct" in engine.answer("details of DL-0034")["text"]


@pytest.mark.parametrize("q,reason", [
    ("Sailings from Rotterdam to Singapore", "no_data"),
    ("Details of sailing DL-9999", "no_data"),
    ("freight rate from Singapore to Rotterdam", "out_of_scope"),
])
def test_refusals_carry_no_facts(q, reason):
    res = engine.answer(q)
    assert res["refused"] and res["parts"][0]["reason"] == reason
    assert not re.search(r"\d", res["text"]) and res["parts"][0]["evidence"] == {}


def test_every_refusal_template_is_free_of_numbers_and_ports():
    from ssa.parser import find_ports
    for text in engine.REFUSALS.values():
        assert not re.search(r"\d", text) and find_ports(text.lower()) == []


def test_unknown_faq_or_op_is_refused():
    assert engine.run_part({"op": "faq", "faq_id": "FAQ-99"}, "2026-11-16")["op"] == "refuse"
    assert engine.run_part({"op": "delete"}, "2026-11-16")["op"] == "refuse"


def test_runtime_guard_blocks_an_ungrounded_answer(monkeypatch):
    real = engine.compose
    monkeypatch.setattr(engine, "compose",
                        lambda part, rows: (real(part, rows)[0].replace("2026-11-24", "2026-11-25"), None))
    part = engine.answer("details of DL-0034")["parts"][0]
    assert part["op"] == "refuse" and part["reason"] == "guard_blocked"


def test_faq_answer_is_the_authored_text():
    part = engine.answer("What is VGM?")["parts"][0]
    entry = next(e for e in data.faq() if e["id"] == "FAQ-03")
    assert part["text"] == entry["answer"] + " [FAQ-03]"


# ---- guard -----------------------------------------------------------------

def _detail():
    part = engine.answer("details of DL-0045")["parts"][0]
    return part["text"], part["evidence"]


@pytest.mark.parametrize("old,new,word", [
    ("2026-11-27", "2026-11-28", "date"),
    ("16:00", "16:30", "time"),
    ("30 days", "31 days", "number"),
    ("Rotterdam (NLRTM)", "Hamburg (DEHAM)", "port"),
    ("619E", "620E", "number"),
])
def test_guard_catches_tampering(old, new, word):
    text, ev = _detail()
    assert old in text
    problems = guard.check(text.replace(old, new), ev)
    assert problems and word in problems[0]


def test_guard_requires_cited_records_to_be_retrieved():
    text, ev = _detail()
    assert guard.check(text.replace("[DL-0045]", "[DL-0001]"), ev)
    assert guard.check("ETD 2026-11-27 with no citation", ev)


def test_guard_binds_each_line_to_its_own_citation():
    part = engine.answer("Which sailings go from Singapore to Rotterdam next week?")["parts"][0]
    # 25 days belongs to DL-0034; moving it onto the DL-0045 line must fail
    swapped = part["text"].replace("30 days", "25 days")
    assert guard.check(swapped, part["evidence"])


def test_guard_allows_only_the_citation_count_as_a_derived_number():
    part = engine.answer("how many sailings from Port Klang to Dubai")["parts"][0]
    assert guard.check(part["text"], part["evidence"]) == []
    assert guard.check(part["text"].replace("has 6 matching", "has 7 matching"), part["evidence"])


# ---- optional LLM parser (no model needed) -----------------------------------

def test_llm_validate_accepts_good_parts():
    good = [{"op": "list", "origin": "SGSIN", "dest": "NLRTM", "etd_from": "2026-11-23", "junk": 1},
            {"op": "faq", "faq_id": "FAQ-01"}]
    assert llm.validate(good) == [
        {"op": "list", "origin": "SGSIN", "dest": "NLRTM", "etd_from": "2026-11-23"},
        {"op": "faq", "faq_id": "FAQ-01"}]


@pytest.mark.parametrize("bad", [
    None, [], "list",
    [{"op": "list", "origin": "SGSIN", "dest": "XXXXX"}],
    [{"op": "list", "origin": "SGSIN"}],
    [{"op": "drop_table", "origin": "SGSIN", "dest": "NLRTM"}],
    [{"op": "list", "origin": "SGSIN", "dest": "NLRTM", "etd_from": "next week"}],
    [{"op": "list", "origin": "SGSIN", "dest": "NLRTM", "carrier": "Real Carrier"}],
    [{"op": "cutoff", "sailing_id": "DL-0034", "field": "price"}],
    [{"op": "detail", "origin": "SGSIN", "dest": "NLRTM"}],
    [{"op": "detail", "sailing_id": "0034"}],
    [{"op": "faq", "faq_id": "FAQ-77"}],
    [{"op": "refuse", "reason": "because"}],
    [{"op": "list", "origin": "SGSIN", "dest": "NLRTM"}] * 3,
])
def test_llm_validate_rejects_bad_parts(bad):
    assert llm.validate(bad) is None


class _Fake:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        import json
        return json.dumps({"response": self.payload}).encode("utf-8")


def test_llm_output_is_used_when_valid(monkeypatch):
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: _Fake(
        '{"parts": [{"op": "next", "origin": "HKHKG", "dest": "SGSIN"}]}'))
    parts, name = llm.parse_with_ollama("when can I go", "2026-11-16", "fake")
    assert name == "llm:fake" and engine.answer("x", parts=parts)["parts"][0]["ids"] == ["DL-0016"]


def test_llm_falls_back_to_rules_on_invalid_output_or_no_server(monkeypatch):
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: _Fake(
        '{"parts": [{"op": "list", "origin": "SGSIN", "dest": "Atlantis"}]}'))
    parts, name = llm.parse_with_ollama("What is VGM?", "2026-11-16", "fake")
    assert name == "rule-fallback" and parts == [{"op": "faq", "faq_id": "FAQ-03"}]

    def boom(req, timeout):
        raise OSError("no server")
    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    assert llm.parse_with_ollama("What is VGM?", "2026-11-16", "fake")[1] == "rule-fallback"


def test_llm_prompt_lists_ports_and_computes_next_week():
    prompt = llm.build_prompt("q?", "2026-11-18")
    assert "Rotterdam=NLRTM" in prompt and '"etd_from": "2026-11-23", "etd_to": "2026-11-29"' in prompt
