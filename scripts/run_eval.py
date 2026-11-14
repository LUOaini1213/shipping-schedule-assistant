"""Run the evaluation set and write results/eval.json.

    python scripts/run_eval.py                 rule parser, all splits
    python scripts/run_eval.py --check         fail if results/eval.json is stale
    python scripts/run_eval.py --first-run S   record split S in results/first_run.json (once)
    python scripts/run_eval.py --llm MODEL     optional local-LLM parser -> results/eval_llm.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from eval import oracle  # noqa: E402
from ssa import data, engine, llm  # noqa: E402

RESULTS = ROOT / "results"


def literal_hallucinations(part):
    """Harness-side check, written separately from src/ssa/guard.py: every
    date, number and port in the answer must occur in the retrieved records.
    The only derived number allowed is the count of retrieved records."""
    ev = " ".join(str(v) for rec in part["evidence"].values()
                  for k, v in rec.items() if k != "keywords")
    text = part["text"]
    bad = [d for d in re.findall(r"\d{4}-\d{2}-\d{2}", text) if d not in ev]
    ev_nums = set(re.findall(r"\d+", ev)) | {str(len(part["evidence"]))}
    bad += [n for n in re.findall(r"\d+", text) if n not in ev_nums]
    for p in data.ports():
        named = re.search(r"\b" + re.escape(p["name"]) + r"\b", text) or p["code"] in text
        if named and p["code"] not in ev and p["name"] not in ev:
            bad.append(p["name"])
    return bad


def evaluate(parser_fn):
    expected = oracle.build()
    items = []
    for q in oracle.load_questions():
        parts, name = parser_fn(q["q"])
        res = engine.answer(q["q"], parts=parts, parser_name=name)
        got, exp = engine.key(res), expected[q["id"]]
        answered = [p for p in res["parts"] if p["op"] != "refuse"]
        items.append({
            "id": q["id"], "split": q["split"], "question": q["q"], "parser": name,
            "expected": exp, "got": got, "correct": got == exp,
            "should_refuse": all(p["op"] == "refuse" for p in exp),
            "refused": res["refused"],
            "answer_parts": len(answered),
            "unsupported_tokens": sorted({t for p in answered for t in literal_hallucinations(p)}),
        })
    return items


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def summarise(items):
    ans = [i for i in items if not i["should_refuse"]]
    ref = [i for i in items if i["should_refuse"]]
    parts = sum(i["answer_parts"] for i in items)
    halluc = sum(1 for i in items if i["unsupported_tokens"])
    ans_ok = sum(i["correct"] for i in ans)
    ref_ok = sum(i["correct"] for i in ref)
    return {
        "questions": len(items),
        "answerable": len(ans),
        "answerable_correct": ans_ok,
        "execution_accuracy_pct": pct(ans_ok, len(ans)),
        "should_refuse": len(ref),
        "refused_with_correct_reason": ref_ok,
        "refusal_correctness_pct": pct(ref_ok, len(ref)),
        "refused_any_reason": sum(i["refused"] for i in ref),
        "false_refusals": sum(i["refused"] for i in ans),
        "wrong_answers_given": sum(1 for i in ans if not i["correct"] and not i["refused"]),
        "answered_but_should_refuse": sum(1 for i in ref if not i["refused"]),
        "answer_parts_checked": parts,
        "answers_with_unsupported_tokens": halluc,
        "hallucination_rate_pct": pct(halluc, parts),
    }


def report(items):
    splits = sorted({i["split"] for i in items})
    out = {"as_of": data.meta()["as_of"], "summary": {"all": summarise(items)}}
    for s in splits:
        out["summary"][s] = summarise([i for i in items if i["split"] == s])
    out["failures"] = [{k: i[k] for k in ("id", "split", "question", "expected", "got")}
                       for i in items if not i["correct"]]
    out["items"] = [{k: i[k] for k in ("id", "split", "parser", "correct", "refused",
                                        "unsupported_tokens")} for i in items]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--first-run", metavar="SPLIT")
    ap.add_argument("--llm", metavar="MODEL")
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    as_of = data.meta()["as_of"]
    if a.llm:
        rep = report(evaluate(lambda q: llm.parse_with_ollama(q, as_of, a.llm)))
        rep["model"] = a.llm
        rep["fallbacks_to_rule_parser"] = sum(i["parser"] == "rule-fallback" for i in rep["items"])
        rep["note"] = "Optional run on one machine; not reproduced in CI."
        (RESULTS / "eval_llm.json").write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(rep["summary"], indent=1))
        return
    rep = report(evaluate(lambda q: (None, "rule")))
    text = json.dumps(rep, indent=1) + "\n"
    path = RESULTS / "eval.json"
    if a.check:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            sys.exit("results/eval.json is stale: run scripts/run_eval.py")
        print("results/eval.json is up to date")
        return
    if a.first_run:
        fr_path = RESULTS / "first_run.json"
        fr = json.loads(fr_path.read_text(encoding="utf-8")) if fr_path.exists() else {}
        if a.first_run in fr:
            sys.exit(f"first run for {a.first_run} is already recorded")
        fr[a.first_run] = {"summary": rep["summary"][a.first_run],
                           "failed_ids": [f["id"] for f in rep["failures"] if f["split"] == a.first_run]}
        fr_path.write_text(json.dumps(fr, indent=1) + "\n", encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    for s, v in rep["summary"].items():
        print(s, v["answerable_correct"], "/", v["answerable"], "exec |",
              v["refused_with_correct_reason"], "/", v["should_refuse"], "refusal |",
              v["answers_with_unsupported_tokens"], "unsupported")
    for f in rep["failures"]:
        if f["split"] != "blind":
            print("FAIL", f["id"], f["question"], "\n   exp", f["expected"], "\n   got", f["got"])
        else:
            print("FAIL", f["id"])


if __name__ == "__main__":
    main()
