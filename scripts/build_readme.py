"""Generate README.md from results/. Every number in the README comes from a
results file; tests/test_repo.py fails if one does not.

    python scripts/build_readme.py           write
    python scripts/build_readme.py --check   fail if README.md is stale
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SET_NAMES = [("dev", "Author set A (dev)"), ("heldout", "Author set B"),
             ("blind", "Blind set one"), ("blind2", "Blind set two")]


def load(name):
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def row(label, s, note=""):
    return (f"| {label} | {s['answerable_correct']}/{s['answerable']} | {s['execution_accuracy_pct']}% "
            f"| {s['refused_with_correct_reason']}/{s['should_refuse']} | {s['wrong_answers_given']} "
            f"| {s['false_refusals']} | {s['answered_but_should_refuse']} "
            f"| {s['answers_with_unsupported_tokens']}/{s['answer_parts_checked']} | {note} |")


HEAD = ("| Question set | Execution accuracy | | Refused with right reason | Wrong answers given "
        "| False refusals | Answered but should refuse | Ungrounded answers | Note |\n"
        "|---|---|---|---|---|---|---|---|---|")


def build():
    ev, first, mut, llm = load("eval.json"), load("first_run.json"), load("mutation.json"), load("eval_llm.json")
    ds, summ = ev["dataset"], ev["summary"]
    L = []
    add = L.append
    add("Personal product project; sample data is fictional; not affiliated with any carrier.")
    add("")
    add("# Shipping Schedule Assistant")
    add("")
    add("A shipper-facing assistant for container sailing schedules and booking questions: "
        "which sailings run from port A to port B, transit time, cut-offs, and what you need to book. "
        "It is a product exercise - research, PRD, clickable prototype, working demo and an evaluation "
        "that reports where it fails.")
    add("")
    add("> **The schedule is invented.** Carriers (\"Demo Line ...\"), vessels, voyages, dates, transit "
        "times and cut-offs are produced by a seeded generator. Only the port names and UN/LOCODEs are real. "
        "Nothing here is, or is derived from, any carrier's schedule.")
    add("")
    add("## What is in the repo")
    add("")
    add("| Deliverable | Where |")
    add("|---|---|")
    add("| Landscape and competitor analysis, with sources and what could not be verified | "
        "[docs/competitor_analysis.md](docs/competitor_analysis.md), [docs/sources.md](docs/sources.md) |")
    add("| PRD | [docs/PRD.md](docs/PRD.md) |")
    add("| Clickable prototype (static HTML/CSS/JS, no external assets; hand-written, no design tool) | "
        "[prototype/index.html](prototype/index.html) |")
    add("| Working demo | `python scripts/ask.py \"...\"` |")
    add("| Evaluation | [eval/](eval/), `python scripts/run_eval.py`, [results/](results/) |")
    add("")
    add("## How an answer is produced")
    add("")
    add("```")
    add("question -> parser -> validated query -> retrieve rows / FAQ entry -> template -> grounding guard -> answer or refusal")
    add("```")
    add("")
    add("- The parser is a rule parser. Optionally a local model served by Ollama fills in the same "
        "structured query; its output is validated and it never writes answer text. Tests and CI do not need it.")
    add("- Answers are templates filled only from retrieved rows and FAQ entries, each line citing its record.")
    add("- Before an answer is returned, every date, time, number and port on each line must appear in the "
        "records that line cites; otherwise the answer is replaced by a refusal.")
    add("- It refuses when the question is out of scope, names an unknown port, lacks an origin or "
        "destination, or matches no data.")
    add("")
    add(f"Sample data: {ds['sailings']} fictional sailings on {ds['lanes']} lanes between {ds['ports']} real ports, "
        f"{ds['carriers']} invented carriers, {ds['faq_entries']} authored FAQ entries. "
        f"The demo's \"today\" is fixed (`as_of = {ev['as_of']}`).")
    add("")
    add("## Evaluation")
    add("")
    add(f"{summ['all']['questions']} questions in four sets. Expected answers are computed by "
        "[eval/oracle.py](eval/oracle.py), which filters the CSV directly from hand-written labels and imports "
        "nothing from the product code.")
    add("")
    add("How independent the sets really are:")
    add("")
    add("- **Author sets A and B** were written and committed before any parser code existed, "
        "but by the same author who then wrote the parser. Treat them as regression tests, not as a measure of quality.")
    add("- **Blind sets one and two** were each written by a separate AI agent session that was given the data, "
        "the label format and the reading conventions, and was told not to open the parser. "
        "The parser was committed before each blind set was added (see `git log`). "
        "Caveat: a hand-back summary of blind set one mentioned a few phrasings before its first run; "
        "the parser plan was not changed in response, but the set is not perfectly blind. Blind set two was run with no such leak.")
    add("- The blind sets are synthetic. They are not real shipper questions.")
    add("")
    add("### First run of each set (never re-run after changes)")
    add("")
    add(HEAD)
    for key, label in SET_NAMES:
        f = first[key]
        add(row(label, f["summary"], f"parser {f['parser']}"))
    add("")
    v1 = first["blind2_parser_v1"]["summary"]
    v2 = first["blind2"]["summary"]
    add("### One iteration, measured on unseen questions")
    add("")
    add("Parser v1 failed on blind set one, the failures were grouped into categories, and v2 fixed the "
        "categories. Blind set two was then written and run on both versions:")
    add("")
    add(HEAD)
    add(row("Blind set two", v1, "parser v1"))
    add(row("Blind set two", v2, "parser v2"))
    add("")
    add("So the iteration helped, modestly, and a rule parser still gets only about half of unseen "
        "answerable phrasings exactly right. That is the main finding and the reason parsing is phase one of the roadmap.")
    add("")
    add("### Current state (parser v2, all sets)")
    add("")
    add(HEAD)
    for key, label in SET_NAMES:
        note = "tuned on this set" if key == "blind" else ("regression" if key in ("dev", "heldout") else "not tuned on")
        add(row(label, summ[key], note))
    add("")
    add("Blind set one is at its ceiling here only because v2 was written from its failures.")
    add("")
    add("### Hallucination check")
    add("")
    a = summ["all"]
    add(f"{a['answers_with_unsupported_tokens']} of {a['answer_parts_checked']} answers contained a date, "
        "number or port that was not in the retrieved records. This check lives in the evaluation harness "
        "and is separate from the runtime guard. Because answers are templates over retrieved rows this is "
        "true by construction; the check is there to catch regressions, and the mutation tests confirm it can fail. "
        "**It does not catch a misread question**: the wrong-answer column above counts answers that are "
        "fully grounded in real sample rows but answer a different question than the one asked.")
    add("")
    add("### Failure cases (blind set two, parser v2)")
    add("")
    add("| ID | Question | Expected | Got |")
    add("|---|---|---|---|")
    for f in ev["failures"]:
        def short(parts):
            return "; ".join(p["op"] + (":" + p["reason"] if p["op"] == "refuse" else "") for p in parts)
        add(f"| `{f['id']}` | {f['question']} | {short(f['expected'])} | {short(f['got'])} |")
    add("")
    add("Patterns: superlatives and counts phrased without the trigger words fall back to a plain list "
        "(right lane, too many rows); a cut-off asked as \"when does X close\" is answered with the full "
        "sailing detail; FAQ questions without a keyword are refused; the second part of a two-part "
        "question is dropped when its FAQ topic is not on the allow-list.")
    add("")
    if llm:
        add("### Optional: a local model as the parser")
        add("")
        add(f"One run of `{llm['model']}` through Ollama on the two blind sets, same validation and same "
            "answer templates. Not reproduced in CI. The prompt was written after the blind failures above "
            "had been seen, so this is an indication, not a blind result.")
        add("")
        add(HEAD)
        for key, label in SET_NAMES[2:]:
            add(row(label, llm["summary"][key], "local model"))
        add("")
        add(f"The model's output failed validation on {llm['fallbacks_to_rule_parser']} of "
            f"{llm['summary']['all']['questions']} questions and fell back to the rule parser. "
            "It reads unusual phrasings better than the rules but is worse at refusing: it answers "
            "questions it should decline. Grounding still holds, because it never writes the answer.")
        add("")
    add("## Tests and mutation testing")
    add("")
    m1, m2 = mut["first"], mut["final"]
    add(f"Offline pytest suite: {m2['tests_in_suite']} tests. Mutation testing plants one bug at a time "
        f"(`python scripts/mutation_test.py`): first run {m1['killed']}/{m1['mutants']} killed "
        f"with {m1['tests_in_suite']} tests; final run {m2['killed']}/{m2['mutants']} killed.")
    if m1["survivors"]:
        add("")
        add("Survivors of the first run, each of which led to a new or stronger test: "
            + "; ".join(m1["survivors"]) + ".")
    if m2["survivors"]:
        add("")
        add("Still surviving: " + "; ".join(m2["survivors"]) + ".")
    add("")
    add("## Run it")
    add("")
    add("```")
    add("python -m venv .venv")
    add(".venv/Scripts/python -m pip install -r requirements.txt     # Windows; use .venv/bin/python elsewhere")
    add(".venv/Scripts/python -m pytest -q")
    add(".venv/Scripts/python scripts/ask.py \"Which sailings go from Singapore to Rotterdam next week?\"")
    add(".venv/Scripts/python scripts/run_eval.py")
    add(".venv/Scripts/python scripts/build_readme.py")
    add("```")
    add("")
    add("Open `prototype/index.html` in a browser for the prototype. It replays real engine output for a "
        "fixed list of questions; free text is answered by `scripts/ask.py`.")
    add("")
    add("## Limitations")
    add("")
    add("- Sample data only: no real feed, no freshness problem actually solved, no multi-leg routings.")
    add("- No users: the PRD's online metrics are a measurement plan, not results.")
    add("- The research is desk research on public pages; see docs/sources.md for what could not be verified.")
    add("- English only; rule parser; the question sets are small and synthetic.")
    add("- \"Next sailing\" does not skip a sailing whose cut-off has already passed.")
    add("- The FAQ is general guidance written for this demo, not carrier policy or legal advice.")
    add("")
    add("## Licence")
    add("")
    add("MIT, see [LICENSE](LICENSE).")
    return "\n".join(L) + "\n"


def main():
    text = build()
    path = ROOT / "README.md"
    if "--check" in sys.argv:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            sys.exit("README.md is stale: run scripts/build_readme.py")
        print("README.md is up to date")
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print("wrote README.md")


if __name__ == "__main__":
    main()
