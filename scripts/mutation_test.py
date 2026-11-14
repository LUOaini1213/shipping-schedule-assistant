"""Mutation test: plant one bug at a time in a temporary copy of the repo and
check that the offline test suite fails.

    python scripts/mutation_test.py --label first    record the first run (kept forever)
    python scripts/mutation_test.py                  record the final run

Results go to results/mutation.json. A surviving mutant means the tests cannot
see that bug; survivors of the first run are listed in the file.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = shutil.ignore_patterns(".venv", ".git", "__pycache__", ".pytest_cache")

# (name, file, old text, new text) - old text must occur exactly once
MUTANTS = [
    ("next week starts one week late", "src/ssa/parser.py",
     "_iso(monday + timedelta(days=7)), _iso(monday + timedelta(days=13))",
     "_iso(monday + timedelta(days=14)), _iso(monday + timedelta(days=20))"),
    ("this week ends on Saturday", "src/ssa/parser.py",
     "_iso(monday), _iso(monday + timedelta(days=6))", "_iso(monday), _iso(monday + timedelta(days=5))"),
    ("week anchored on today instead of Monday", "src/ssa/parser.py",
     "monday = as_of - timedelta(days=as_of.weekday())", "monday = as_of"),
    ("'before X' includes X", "src/ssa/parser.py",
     'out["etd_to"] = _iso(d - timedelta(days=1))', 'out["etd_to"] = _iso(d)'),
    ("next N days off by one", "src/ssa/parser.py",
     "_iso(as_of), _iso(as_of + timedelta(days=n))", "_iso(as_of), _iso(as_of + timedelta(days=n - 1))"),
    ("month range ends one day early", "src/ssa/parser.py",
     "_iso(first), _iso(nxt - timedelta(days=1))", "_iso(first), _iso(nxt - timedelta(days=2))"),
    ("origin cue ignored", "src/ssa/parser.py",
     "if ORIGIN_CUE.search(before) and origin is None:", "if False and origin is None:"),
    ("vgm field falls back to cy", "src/ssa/parser.py",
     '"vgm_cutoff" if "vgm" in text else', '"cy_cutoff" if "vgm" in text else'),
    ("sailing id with cut-off word treated as detail", "src/ssa/parser.py",
     '"cutoff" if is_cutoff else "detail", "sailing_id"', '"detail" if is_cutoff else "detail", "sailing_id"'),
    ("direct filter dropped", "src/ssa/parser.py", 'part["direct"] = True', 'part["direct"] = False'),
    ("out-of-scope check disabled", "src/ssa/parser.py",
     "    if OUT_OF_SCOPE.search(text):", "    if False and OUT_OF_SCOPE.search(text):"),
    ("unknown port never detected", "src/ssa/parser.py",
     "    if has_unknown_port(raw):", "    if False and has_unknown_port(raw):"),
    ("FAQ tie-break prefers shortest keyword", "src/ssa/parser.py",
     "score = (len(hits), max(len(k) for k in hits))", "score = (len(hits), -max(len(k) for k in hits))"),
    ("cut-off question drags a FAQ part along", "src/ssa/parser.py",
     'if faq_id in COMPOUND_FAQ and part["op"] != "cutoff":', "if faq_id in COMPOUND_FAQ:"),
    ("past departures are returned", "src/ssa/engine.py",
     'lo = max(part.get("etd_from") or as_of, as_of)', 'lo = part.get("etd_from") or "0000"'),
    ("lane direction swapped", "src/ssa/engine.py",
     'if r["origin_code"] == part["origin"] and r["dest_code"] == part["dest"]',
     'if r["origin_code"] == part["dest"] and r["dest_code"] == part["origin"]'),
    ("etd upper bound exclusive", "src/ssa/engine.py",
     'and lo <= r["etd"] <= (part.get("etd_to") or "9999")',
     'and lo <= r["etd"] < (part.get("etd_to") or "9999")'),
    ("eta filter ignored", "src/ssa/engine.py",
     'and r["eta"] <= (part.get("eta_to") or "9999")', 'and r["eta"] <= "9999"'),
    ("carrier filter ignored", "src/ssa/engine.py",
     'and (not part.get("carrier") or r["carrier"] == part["carrier"])]', "and True]"),
    ("fastest returns slowest", "src/ssa/engine.py",
     'best = min(r["transit_days"] for r in hit)', 'best = max(r["transit_days"] for r in hit)'),
    ("earliest arrival returns latest", "src/ssa/engine.py",
     'best = min(r["eta"] for r in hit)', 'best = max(r["eta"] for r in hit)'),
    ("empty retrieval answered instead of refused", "src/ssa/engine.py",
     '        if not rows:\n            return _refusal("no_data", part)\n        text, value = compose(part, rows)',
     '        text, value = compose(part, rows) if rows else ("No sailings.", None)'),
    ("runtime guard switched off", "src/ssa/engine.py",
     "    if guard.check(text, evidence):", "    if False and guard.check(text, evidence):"),
    ("answer shows ETA where ETD belongs", "src/ssa/engine.py",
     "f\"ETD {r['etd']} {_port(r['origin_code'])} to ETA {r['eta']}", "f\"ETD {r['eta']} {_port(r['origin_code'])} to ETA {r['eta']}"),
    ("cut-off answer always shows the CY value", "src/ssa/engine.py",
     "is {r[f]}, \"", "is {r['cy_cutoff']}, \""),
    ("transit minimum reported as maximum", "src/ssa/engine.py",
     "[min(days), max(days)]", "[max(days), max(days)]"),
    ("guard ignores dates", "src/ssa/guard.py", "for d in sorted(dates - ev_dates):", "for d in []:"),
    ("guard ignores ports", "src/ssa/guard.py", "if code not in ev_ports:", "if False:"),
    ("guard accepts any number", "src/ssa/guard.py", "if int(n) != len(cited) or not cited:", "if False:"),
    ("guard pools evidence across lines", "src/ssa/guard.py",
     'ev_text = " ".join(record_text(evidence[c]) for c in cited)',
     'ev_text = " ".join(record_text(evidence[c]) for c in evidence)'),
    ("guard accepts citations of unretrieved records", "src/ssa/guard.py",
     "missing = [c for c in cited if c not in evidence]", "missing = []"),
    ("LLM port codes not validated", "src/ssa/llm.py",
     'elif p.get("origin") in codes and p.get("dest") in codes:', 'elif p.get("origin") and p.get("dest"):'),
    ("LLM cut-off field not validated", "src/ssa/llm.py",
     'if p.get("field") not in FIELDS:', "if False:"),
    ("LLM failure does not fall back", "src/ssa/llm.py",
     'return parse(question, date.fromisoformat(as_of)), "rule-fallback"', 'return [], "rule-fallback"'),
    ("oracle keeps past departures", "eval/oracle.py",
     'lo = max(spec.get("etd_from", AS_OF), AS_OF)', 'lo = spec.get("etd_from", "0000")'),
    ("harness counts every question as correct", "scripts/run_eval.py",
     '"expected": exp, "got": got, "correct": got == exp,', '"expected": exp, "got": got, "correct": True,'),
    ("harness hallucination check disabled", "scripts/run_eval.py",
     "    bad += [n for n in re.findall(r\"\\d+\", text) if n not in ev_nums]", "    bad += []"),
    ("README shows refusal count in the accuracy column", "scripts/build_readme.py",
     "{s['answerable_correct']}/{s['answerable']}", "{s['refused_with_correct_reason']}/{s['answerable']}"),
    ("sample data seed changed", "scripts/build_sample_data.py", "SEED = 20261114", "SEED = 20261115"),
    ("a FAQ answer edited without review", "data/faq.json",
     "before the VGM cut-off of the sailing", "after the VGM cut-off of the sailing"),
]


def run_pytest(cwd):
    p = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"],
                       cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="final", choices=["first", "final"])
    a = ap.parse_args()
    out_path = ROOT / "results" / "mutation.json"
    report = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    if a.label == "first" and report.get("first", {}).get("mutants"):
        sys.exit("first run is already recorded")

    code, out = run_pytest(ROOT)
    if code != 0:
        sys.exit("baseline tests fail; fix them before mutation testing\n" + out[-2000:])
    tests = int(re.search(r"(\d+) passed", out).group(1))

    survivors = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, rel, old, new) in enumerate(MUTANTS):
            work = Path(tmp) / f"m{i}"
            shutil.copytree(ROOT, work, ignore=SKIP)
            path = work / rel
            src = path.read_text(encoding="utf-8")
            if src.count(old) != 1:
                sys.exit(f"mutant '{name}': target text occurs {src.count(old)} times in {rel}")
            path.write_text(src.replace(old, new), encoding="utf-8", newline="\n")
            code, _ = run_pytest(work)
            print("killed  " if code != 0 else "SURVIVED", name, flush=True)
            if code == 0:
                survivors.append(name)
            shutil.rmtree(work, ignore_errors=True)
    report[a.label] = {"mutants": len(MUTANTS), "killed": len(MUTANTS) - len(survivors),
                       "survived": len(survivors), "survivors": survivors, "tests_in_suite": tests}
    out_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{a.label}: {len(MUTANTS) - len(survivors)}/{len(MUTANTS)} killed, {tests} tests")


if __name__ == "__main__":
    main()
