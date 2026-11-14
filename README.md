Personal product project; sample data is fictional; not affiliated with any carrier.

# Shipping Schedule Assistant

A shipper-facing assistant for container sailing schedules and booking questions: which sailings run from port A to port B, transit time, cut-offs, and what you need to book. It is a product exercise - research, PRD, clickable prototype, working demo and an evaluation that reports where it fails.

> **The schedule is invented.** Carriers ("Demo Line ..."), vessels, voyages, dates, transit times and cut-offs are produced by a seeded generator. Only the port names and UN/LOCODEs are real. Nothing here is, or is derived from, any carrier's schedule.

## What is in the repo

| Deliverable | Where |
|---|---|
| Landscape and competitor analysis, with sources and what could not be verified | [docs/competitor_analysis.md](docs/competitor_analysis.md), [docs/sources.md](docs/sources.md) |
| PRD | [docs/PRD.md](docs/PRD.md) |
| Clickable prototype (static HTML/CSS/JS, no external assets; hand-written, no design tool) | [prototype/index.html](prototype/index.html) |
| Working demo | `python scripts/ask.py "..."` |
| Evaluation | [eval/](eval/), `python scripts/run_eval.py`, [results/](results/) |

## How an answer is produced

```
question -> parser -> validated query -> retrieve rows / FAQ entry -> template -> grounding guard -> answer or refusal
```

- The parser is a rule parser. Optionally a local model served by Ollama fills in the same structured query; its output is validated and it never writes answer text. Tests and CI do not need it.
- Answers are templates filled only from retrieved rows and FAQ entries, each line citing its record.
- Before an answer is returned, every date, time, number and port on each line must appear in the records that line cites; otherwise the answer is replaced by a refusal.
- It refuses when the question is out of scope, names an unknown port, lacks an origin or destination, or matches no data.

Sample data: 151 fictional sailings on 21 lanes between 12 real ports, 3 invented carriers, 12 authored FAQ entries. The demo's "today" is fixed (`as_of = 2026-11-16`).

## Evaluation

124 questions in four sets. Expected answers are computed by [eval/oracle.py](eval/oracle.py), which filters the CSV directly from hand-written labels and imports nothing from the product code.

How independent the sets really are:

- **Author sets A and B** were written and committed before any parser code existed, but by the same author who then wrote the parser. Treat them as regression tests, not as a measure of quality.
- **Blind sets one and two** were each written by a separate AI agent session that was given the data, the label format and the reading conventions, and was told not to open the parser. The parser was committed before each blind set was added (see `git log`). Caveat: a hand-back summary of blind set one mentioned a few phrasings before its first run; the parser plan was not changed in response, but the set is not perfectly blind. Blind set two was run with no such leak.
- The blind sets are synthetic. They are not real shipper questions.

### First run of each set (never re-run after changes)

| Question set | Execution accuracy | | Refused with right reason | Wrong answers given | False refusals | Answered but should refuse | Ungrounded answers | Note |
|---|---|---|---|---|---|---|---|---|
| Author set A (dev) | 22/22 | 100.0% | 10/10 | 0 | 0 | 0 | 0/23 | parser v1 |
| Author set B | 22/22 | 100.0% | 10/10 | 0 | 0 | 0 | 0/23 | parser v1 |
| Blind set one | 9/18 | 50.0% | 8/12 | 6 | 3 | 0 | 0/16 | parser v1 |
| Blind set two | 10/18 | 55.6% | 11/12 | 6 | 2 | 0 | 0/16 | parser v2 |

### One iteration, measured on unseen questions

Parser v1 failed on blind set one, the failures were grouped into categories, and v2 fixed the categories. Blind set two was then written and run on both versions:

| Question set | Execution accuracy | | Refused with right reason | Wrong answers given | False refusals | Answered but should refuse | Ungrounded answers | Note |
|---|---|---|---|---|---|---|---|---|
| Blind set two | 8/18 | 44.4% | 8/12 | 8 | 2 | 1 | 0/17 | parser v1 |
| Blind set two | 10/18 | 55.6% | 11/12 | 6 | 2 | 0 | 0/16 | parser v2 |

So the iteration helped, modestly, and a rule parser still gets only about half of unseen answerable phrasings exactly right. That is the main finding and the reason parsing is phase one of the roadmap.

### Current state (parser v2, all sets)

| Question set | Execution accuracy | | Refused with right reason | Wrong answers given | False refusals | Answered but should refuse | Ungrounded answers | Note |
|---|---|---|---|---|---|---|---|---|
| Author set A (dev) | 22/22 | 100.0% | 10/10 | 0 | 0 | 0 | 0/23 | regression |
| Author set B | 22/22 | 100.0% | 10/10 | 0 | 0 | 0 | 0/23 | regression |
| Blind set one | 18/18 | 100.0% | 12/12 | 0 | 0 | 0 | 0/20 | tuned on this set |
| Blind set two | 10/18 | 55.6% | 11/12 | 6 | 2 | 0 | 0/16 | not tuned on |

Blind set one is at its ceiling here only because v2 was written from its failures.

### Hallucination check

0 of 82 answers contained a date, number or port that was not in the retrieved records. This check lives in the evaluation harness and is separate from the runtime guard. Because answers are templates over retrieved rows this is true by construction; the check is there to catch regressions, and the mutation tests confirm it can fail. **It does not catch a misread question**: the wrong-answer column above counts answers that are fully grounded in real sample rows but answer a different question than the one asked.

### Failure cases (blind set two, parser v2)

| ID | Question | Expected | Got |
|---|---|---|---|
| `C02` | what's the ocean freight for a 20' from Yantian to Hamburg these days | refuse:out_of_scope | refuse:no_data |
| `C03` | Which SGSIN-AEJEA service has the lowest number of days at sea? | fastest | list |
| `C04` | If we pull out of a booking a couple of days before the vessel sails, will we get charged for it? | faq | refuse:missing_info |
| `C06` | Our cargo is ready in Yantian and has to go to Rotterdam. Which departure would put it in Rotterdam first? | earliest_arrival | list |
| `C09` | DL-0092 - when does VGM close? | cutoff | detail |
| `C17` | First time exporting here. What information does the carrier want from me when I request a booking? | faq | refuse:out_of_scope |
| `C18` | how many times does a vessel leave Singapore for Port Klang over the next 7 days | count | list |
| `C24` | Transit time Singapore to Hamburg? Also, how do I get the container quantity on my booking changed? | transit; faq | transit |
| `C28` | next week's sailings ningbo to los angeles please, and remind me who has to declare the VGM | list; faq | list |

Patterns: superlatives and counts phrased without the trigger words fall back to a plain list (right lane, too many rows); a cut-off asked as "when does X close" is answered with the full sailing detail; FAQ questions without a keyword are refused; the second part of a two-part question is dropped when its FAQ topic is not on the allow-list.

### Optional: a local model as the parser

One run of `gemma3:4b` through Ollama on the two blind sets, same validation and same answer templates. Not reproduced in CI. The prompt was written after the blind failures above had been seen, so this is an indication, not a blind result.

| Question set | Execution accuracy | | Refused with right reason | Wrong answers given | False refusals | Answered but should refuse | Ungrounded answers | Note |
|---|---|---|---|---|---|---|---|---|
| Blind set one | 11/18 | 61.1% | 5/12 | 6 | 1 | 4 | 0/23 | local model |
| Blind set two | 12/18 | 66.7% | 8/12 | 6 | 0 | 2 | 0/22 | local model |

The model's output failed validation on 9 of 60 questions and fell back to the rule parser. It reads unusual phrasings better than the rules but is worse at refusing: it answers questions it should decline. Grounding still holds, because it never writes the answer.

## Tests and mutation testing

Offline pytest suite: 112 tests. Mutation testing plants one bug at a time (`python scripts/mutation_test.py`): first run 38/40 killed with 110 tests; final run 40/40 killed.

Survivors of the first run, each of which led to a new or stronger test: origin cue ignored; oracle keeps past departures.

## Run it

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Windows; use .venv/bin/python elsewhere
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/ask.py "Which sailings go from Singapore to Rotterdam next week?"
.venv/Scripts/python scripts/run_eval.py
.venv/Scripts/python scripts/build_readme.py
```

Open `prototype/index.html` in a browser for the prototype. It replays real engine output for a fixed list of questions; free text is answered by `scripts/ask.py`.

## Limitations

- Sample data only: no real feed, no freshness problem actually solved, no multi-leg routings.
- No users: the PRD's online metrics are a measurement plan, not results.
- The research is desk research on public pages; see docs/sources.md for what could not be verified.
- English only; rule parser; the question sets are small and synthetic.
- "Next sailing" does not skip a sailing whose cut-off has already passed.
- The FAQ is general guidance written for this demo, not carrier policy or legal advice.

## Licence

MIT, see [LICENSE](LICENSE).
