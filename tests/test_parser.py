from datetime import date

import pytest

from ssa import parser

AS_OF = date(2026, 11, 16)


def one(q):
    parts = parser.parse(q, AS_OF)
    assert len(parts) == 1
    return parts[0]


@pytest.mark.parametrize("text,expected", [
    ("sailings next week", {"etd_from": "2026-11-23", "etd_to": "2026-11-29"}),
    ("sailings this week", {"etd_from": "2026-11-16", "etd_to": "2026-11-22"}),
    ("in the next 14 days", {"etd_from": "2026-11-16", "etd_to": "2026-11-30"}),
    ("over the next two weeks", {"etd_from": "2026-11-16", "etd_to": "2026-11-30"}),
    ("in december", {"etd_from": "2026-12-01", "etd_to": "2026-12-31"}),
    ("in november", {"etd_from": "2026-11-01", "etd_to": "2026-11-30"}),
    ("on 2026-12-09", {"etd_from": "2026-12-09", "etd_to": "2026-12-09"}),
    ("depart on 9 dec", {"etd_from": "2026-12-09", "etd_to": "2026-12-09"}),
    ("depart on dec 9", {"etd_from": "2026-12-09", "etd_to": "2026-12-09"}),
    ("leave after 1 december", {"etd_from": "2026-12-01"}),
    ("before 2026-12-05", {"etd_to": "2026-12-04"}),
    ("by 2026-12-05", {"etd_to": "2026-12-05"}),
    ("between 2026-12-01 and 2026-12-15", {"etd_from": "2026-12-01", "etd_to": "2026-12-15"}),
    ("arriving by 2026-12-25", {"eta_to": "2026-12-25"}),
    ("arriving before 2026-12-25", {"eta_to": "2026-12-24"}),
    ("tomorrow", {"etd_from": "2026-11-17", "etd_to": "2026-11-17"}),
    ("no date here", {}),
    ("we may ship soon", {}),
])
def test_dates(text, expected):
    assert parser.parse_dates(text, AS_OF) == expected


def test_week_is_monday_to_sunday_even_midweek():
    assert parser.parse_dates("next week", date(2026, 11, 19)) == {
        "etd_from": "2026-11-23", "etd_to": "2026-11-29"}


def test_longest_alias_wins_and_order_is_kept():
    codes = [c for _s, _e, c in parser.find_ports("from port klang to hong kong via la")]
    assert codes == ["MYPKG", "HKHKG", "USLAX"]


def test_alias_needs_word_boundary():
    assert parser.find_ports("a lawful plan") == []


@pytest.mark.parametrize("q,origin,dest", [
    ("sailings from Singapore to Rotterdam", "SGSIN", "NLRTM"),
    ("sailings to Rotterdam from Singapore", "SGSIN", "NLRTM"),
    ("what sailings leave Hamburg for Singapore", "DEHAM", "SGSIN"),
    ("sgsin -> nlrtm sailings", "SGSIN", "NLRTM"),
    ("Shenzhen to Dubai sailings", "CNYTN", "AEJEA"),
])
def test_origin_and_destination(q, origin, dest):
    p = one(q)
    assert (p["origin"], p["dest"]) == (origin, dest)


@pytest.mark.parametrize("q,op", [
    ("sailings from Singapore to Rotterdam", "list"),
    ("how many sailings from Singapore to Rotterdam", "count"),
    ("transit time from Singapore to Rotterdam", "transit"),
    ("how many days from Singapore to Rotterdam", "transit"),
    ("fastest sailing from Singapore to Rotterdam", "fastest"),
    ("shortest transit from Singapore to Rotterdam", "fastest"),
    ("which sailing from Singapore to Rotterdam arrives first", "earliest_arrival"),
    ("next sailing from Singapore to Rotterdam", "next"),
    ("cy cut-off for the next sailing from Singapore to Rotterdam", "cutoff"),
])
def test_intent(q, op):
    assert one(q)["op"] == op


@pytest.mark.parametrize("q,field", [
    ("cut-off for DL-0034", "cy_cutoff"),
    ("vgm deadline for DL-0034", "vgm_cutoff"),
    ("SI cut-off for DL-0034", "doc_cutoff"),
    ("documentation closing for dl-0034", "doc_cutoff"),
])
def test_cutoff_field_and_sailing_id(q, field):
    assert one(q) == {"op": "cutoff", "sailing_id": "DL-0034", "field": field}


def test_detail_by_id():
    assert one("tell me about dl-0102") == {"op": "detail", "sailing_id": "DL-0102"}


def test_filters():
    p = one("direct Demo Line Alfa sailings from Singapore to Shanghai")
    assert p["direct"] is True and p["carrier"] == "Demo Line Alfa"
    assert "direct" not in one("sailings from Singapore to Shanghai")


@pytest.mark.parametrize("q,reason", [
    ("freight rate from Singapore to Rotterdam", "out_of_scope"),
    ("where is my container", "out_of_scope"),
    ("has abcu1234567 arrived", "out_of_scope"),
    ("please cancel my booking", "out_of_scope"),
    ("tell me a joke", "out_of_scope"),
    ("", "out_of_scope"),
    ("sailings from Singapore to Santos", "unknown_port"),
    ("transit time ho chi minh to la", "unknown_port"),
    ("next sailing to Hamburg", "missing_info"),
    ("what time is the cut-off", "missing_info"),
])
def test_refusals(q, reason):
    assert one(q) == {"op": "refuse", "reason": reason}


def test_faq_and_compound():
    assert one("How do I cancel my booking?") == {"op": "faq", "faq_id": "FAQ-06"}
    assert one("What happens if I miss the CY cut-off?") == {"op": "faq", "faq_id": "FAQ-04"}
    parts = parser.parse("Sailings from Singapore to Rotterdam, and what documents do I need?", AS_OF)
    assert [p["op"] for p in parts] == ["list", "faq"] and parts[1]["faq_id"] == "FAQ-01"
    # a cut-off lookup never drags a FAQ answer along
    assert len(parser.parse("documentation cut-off for the next sailing from Singapore to Rotterdam", AS_OF)) == 1


def test_faq_keyword_needs_word_boundary():
    # "si" must not match inside "singapore"
    assert parser.match_faq("anything about singapore") is None


def test_origin_cue_beats_word_order():
    p = one("Rotterdam sailings from Singapore")
    assert (p["origin"], p["dest"]) == ("SGSIN", "NLRTM")
