"""Repository-level checks: generated files are current, README numbers come
from results/, the sample is labelled as fiction, and hygiene rules hold."""
import csv
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_prototype_data  # noqa: E402
import build_readme  # noqa: E402
import build_sample_data  # noqa: E402
import run_eval  # noqa: E402
from eval import oracle  # noqa: E402

RESULTS = ROOT / "results"
README = (ROOT / "README.md").read_text(encoding="utf-8")
EVAL = json.loads((RESULTS / "eval.json").read_text(encoding="utf-8"))
FIRST = json.loads((RESULTS / "first_run.json").read_text(encoding="utf-8"))
TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonl", ".csv", ".yml", ".html", ".css", ".js", ".txt", ".ini", ""}
SKIP_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache"}


def repo_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


# ---- README ------------------------------------------------------------------

def test_readme_first_line():
    assert README.splitlines()[0] == ("Personal product project; sample data is fictional; "
                                      "not affiliated with any carrier.")


def test_readme_is_generated_from_results():
    assert README == build_readme.build()


def _numeric_leaves(node, out):
    if isinstance(node, dict):
        for v in node.values():
            _numeric_leaves(v, out)
    elif isinstance(node, list):
        for v in node:
            _numeric_leaves(v, out)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out.add(str(node))


def readme_numbers(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)      # code blocks
    text = re.sub(r"`[^`]*`", " ", text)                    # inline code
    text = re.sub(r"\]\([^)]*\)", "]", text)                # link targets
    return set(re.findall(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?(?![A-Za-z\d])", text))


def allowed_numbers():
    allowed = set()
    for path in RESULTS.glob("*.json"):
        _numeric_leaves(json.loads(path.read_text(encoding="utf-8")), allowed)
    for f in EVAL["failures"]:                              # questions quoted in the README
        allowed |= set(re.findall(r"\d+", f["question"]))
    return allowed


def test_every_readme_number_is_in_a_results_file():
    missing = readme_numbers(README) - allowed_numbers()
    assert not missing, f"README numbers not found in results/: {sorted(missing)}"


def test_readme_number_check_can_fail():
    assert "987654" in readme_numbers(README + "\nWe reached 987654 users.") - allowed_numbers()
    assert readme_numbers("`as_of = 2026-11-16` and parser v2 and [x](a/1.md)") == set()


def test_readme_rows_match_results():
    for key in ("dev", "heldout", "blind", "blind2"):
        s = EVAL["summary"][key]
        assert (f"| {s['answerable_correct']}/{s['answerable']} | {s['execution_accuracy_pct']}% "
                f"| {s['refused_with_correct_reason']}/{s['should_refuse']} |") in README
    f = FIRST["blind"]["summary"]
    assert f"| Blind set one | {f['answerable_correct']}/{f['answerable']} |" in README
    v1 = FIRST["blind2_parser_v1"]["summary"]
    assert f"| Blind set two | {v1['answerable_correct']}/{v1['answerable']} |" in README


# ---- evaluation --------------------------------------------------------------

def test_expected_answers_come_from_the_oracle():
    assert json.loads((ROOT / "eval" / "expected.json").read_text(encoding="utf-8")) == oracle.build()


def test_eval_results_are_current():
    report = run_eval.report(run_eval.evaluate(lambda q: (None, "rule")))
    assert json.loads(json.dumps(report)) == EVAL


def test_question_sets():
    qs = oracle.load_questions()
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids)) and len(qs) >= 40
    splits = {s: sum(q["split"] == s for q in qs) for s in ("dev", "heldout", "blind", "blind2")}
    assert splits == {"dev": 32, "heldout": 32, "blind": 30, "blind2": 30}
    assert EVAL["summary"]["all"]["questions"] == len(qs)


def test_regression_sets_pass_and_blind2_failures_are_the_recorded_ones():
    failed = {f["id"] for f in EVAL["failures"]}
    assert not {i for i in failed if not i.startswith("C")}
    assert sorted(failed) == FIRST["blind2"]["failed_ids"]
    assert EVAL["summary"]["blind2"] == FIRST["blind2"]["summary"]


def test_no_answer_has_unsupported_tokens():
    assert all(i["unsupported_tokens"] == [] for i in EVAL["items"])
    assert EVAL["summary"]["all"]["answers_with_unsupported_tokens"] == 0


def test_harness_hallucination_check_detects_tampering():
    from ssa import engine
    part = dict(engine.answer("details of DL-0045")["parts"][0])
    assert run_eval.literal_hallucinations(part) == []
    for old, new in (("2026-11-27", "2026-11-28"), ("30 days", "31 days"), ("Rotterdam", "Hamburg")):
        assert run_eval.literal_hallucinations(dict(part, text=part["text"].replace(old, new)))


def test_summary_arithmetic():
    items = [
        {"split": "x", "correct": True, "should_refuse": False, "refused": False, "answer_parts": 1, "unsupported_tokens": []},
        {"split": "x", "correct": False, "should_refuse": False, "refused": False, "answer_parts": 1, "unsupported_tokens": ["9"]},
        {"split": "x", "correct": False, "should_refuse": False, "refused": True, "answer_parts": 0, "unsupported_tokens": []},
        {"split": "x", "correct": True, "should_refuse": True, "refused": True, "answer_parts": 0, "unsupported_tokens": []},
        {"split": "x", "correct": False, "should_refuse": True, "refused": False, "answer_parts": 1, "unsupported_tokens": []},
    ]
    s = run_eval.summarise(items)
    assert (s["answerable"], s["answerable_correct"], s["execution_accuracy_pct"]) == (3, 1, 33.3)
    assert (s["should_refuse"], s["refused_with_correct_reason"], s["refusal_correctness_pct"]) == (2, 1, 50.0)
    assert (s["false_refusals"], s["wrong_answers_given"], s["answered_but_should_refuse"]) == (1, 1, 1)
    assert (s["answer_parts_checked"], s["answers_with_unsupported_tokens"]) == (3, 1)


# ---- sample data -------------------------------------------------------------

def test_sample_schedule_is_reproducible_and_labelled_fictional():
    with open(ROOT / "data" / "sample_schedule.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    built = [{k: str(v) for k, v in r.items()} for r in build_sample_data.build()]
    assert [{k: r[k] for k in build_sample_data.FIELDS} for r in built] == rows
    assert all(r["carrier"].startswith("Demo Line ") and r["vessel"].startswith("DEMO ") for r in rows)
    meta = json.loads((ROOT / "data" / "sample_meta.json").read_text(encoding="utf-8"))
    assert "FICTIONAL" in meta["label"] and meta["rows"] == len(rows) == EVAL["dataset"]["sailings"]
    assert all(r["eta"] > r["etd"] and r["cy_cutoff"][:10] < r["etd"] for r in rows)


def test_faq_is_as_reviewed():
    import hashlib
    text = " ".join(e["answer"] for e in json.loads(
        (ROOT / "data" / "faq.json").read_text(encoding="utf-8"))["entries"])
    assert hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] == FAQ_DIGEST


FAQ_DIGEST = "526a325ef215f624"


# ---- prototype ---------------------------------------------------------------

def test_prototype_data_is_current_and_has_no_external_assets():
    assert (ROOT / "prototype" / "data.js").read_text(encoding="utf-8") == build_prototype_data.build()
    for name in ("index.html", "style.css", "app.js", "data.js"):
        text = (ROOT / "prototype" / name).read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text and "//cdn" not in text
    html = (ROOT / "prototype" / "index.html").read_text(encoding="utf-8")
    assert "fictional sample data" in html and "not affiliated with any carrier" in html


# ---- hygiene -----------------------------------------------------------------

def test_ci_workflow_parses_and_runs_the_offline_suite():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    steps = " ".join(str(s.get("run", "")) for job in wf["jobs"].values() for s in job["steps"])
    assert "pytest" in steps and "ollama" not in steps.lower()


def test_licence_and_pinned_requirements():
    assert "MIT License" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    lines = [x for x in (ROOT / "requirements.txt").read_text(encoding="utf-8").split() if x]
    assert lines and all("==" in x for x in lines)


def test_no_absolute_local_paths():
    pattern = re.compile(r"[A-Za-z]:[\\/]+Users|/Users/|/home/[a-z]|AppData")
    bad = [str(p.relative_to(ROOT)) for p in repo_files()
           if p.suffix in TEXT_SUFFIXES and p.name != "test_repo.py"
           and pattern.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not bad, bad


def test_oracle_also_drops_departures_before_today(monkeypatch):
    monkeypatch.setattr(oracle, "AS_OF", "2026-12-10")
    got = oracle.expected_part({"op": "list", "o": "SGSIN", "d": "NLRTM"}, oracle.load_rows())
    assert got["ids"] == ["DL-0095", "DL-0109", "DL-0120", "DL-0134", "DL-0145"]
