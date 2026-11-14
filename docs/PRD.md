# PRD - Schedule Assistant for shippers

Status: personal product project, version 0.2 of this document. The data in the demo is a
fictional sample; nothing here describes a real carrier's system. Research references (S1...)
point to [sources.md](sources.md); the reasoning behind the positioning is in
[competitor_analysis.md](competitor_analysis.md). Evaluation numbers are deliberately not
repeated here: the README is generated from `results/` and is the only place they are stated.

## 1. Users and scenarios

| User | Context | Typical question |
|------|---------|------------------|
| Export coordinator at a small or mid-sized shipper | Books a few containers a week, works with two or three carriers, not a shipping specialist | "Which sailings from Singapore to Rotterdam next week, and what do I need to book?" |
| Freight forwarder operations staff | Many lanes a day, knows the vocabulary, short of time | "doc cut-off next direct sailing Shanghai to LA" |
| Customer-service agent at a carrier or agency | Answers the same schedule and document questions by phone, chat and email | Looks up the answer on the customer's behalf and needs to trust and forward it |

Scenarios the first release serves:

1. **Plan a shipment** - find sailings on a lane in a date window; compare transit time and routing.
2. **Hit a deadline** - find the CY, documentation or VGM cut-off of a specific or the next sailing.
3. **Work back from arrival** - "it has to arrive by the 25th; which sailings still work?"
4. **Prepare the booking** - what to provide for a booking, shipping instructions, VGM, dangerous goods, bill-of-lading types.
5. **Check an answer** - see exactly which record an answer came from before acting on it.

## 2. Problem statement

Carrier schedule pages answer a form (origin, destination, dates) one carrier at a time (S1-S5).
A shipper's real question is usually one step further - a deadline, a comparison, an
arrival constraint, or "and what do I need" - and getting there means running a search,
opening results and reading values off, then looking for booking guidance somewhere else.
Chat assistants can take the question directly, but in this domain a fluent wrong answer is
worse than no answer: a made-up cut-off means a rolled container and a dispute about who said what.

**The product bet:** a question-first assistant is only useful to shippers if every fact in an
answer is traceable to a schedule record, and if it refuses when the data is not there.

## 3. Scope and non-goals

In scope (this release):

- Point-to-point sailing lookup with date windows, direct-only and carrier filters.
- Transit time, fastest sailing, earliest arrival, next sailing, count of sailings.
- CY, documentation and VGM cut-offs for a sailing.
- A short authored FAQ on booking and documents.
- Citations on every answer and a "source of this answer" view.
- Explicit refusals: out of scope, unknown port, missing origin or destination, no data.

Non-goals:

- **Freight rates, quotes and surcharges.** Different data and commercial sensitivity.
- **Track and trace.** A different object (a container) and a different data feed.
- **Making, changing or cancelling a booking.** The assistant explains how; it does not act.
- **Customs duty or regulatory advice** beyond the general FAQ.
- **Predicting delays or "likely" dates.** Only published values are shown.
- **Languages other than English** in this release.

## 4. User stories and acceptance criteria

| # | As a... | I want... | Acceptance criteria |
|---|---------|-----------|---------------------|
| U1 | export coordinator | to ask which sailings run between two ports in a period | Returns exactly the sailings on that lane whose ETD is in the period and not before today; each with carrier, vessel, voyage, ETD, ETA, transit days, routing and cut-offs; each line cites its record. If none match, the answer says so and lists nothing. |
| U2 | forwarder | the cut-off of a given or the next sailing | Returns the requested cut-off (CY by default; documentation or VGM when asked) with the sailing it belongs to and the time basis. "Next" means the earliest ETD that matches. Never returns a cut-off for a sailing that is not cited. |
| U3 | export coordinator | to work back from a required arrival date | "Arriving by D" returns only sailings with ETA on or before D. |
| U4 | any user | transit time on a lane | States the minimum and maximum transit days over the matching sailings and how many sailings that covers. |
| U5 | any user | booking and document guidance | Returns the single matching FAQ entry verbatim with its ID. If no entry matches, the question is refused, not improvised. |
| U6 | any user | to see where an answer came from | One click from any answer shows how the question was read (ports, dates, intent) and the full retrieved records; the cited record is highlighted. |
| U7 | any user | a clear "I can't answer that" | Refusals name the reason category, contain no dates, numbers or port names, and suggest what to provide when information is missing. |
| U8 | product owner | no ungrounded facts | Before display, every date, time, number and port in each answer line is checked against the records that line cites; the only derived number allowed is the count of cited records. A failing answer is replaced by a refusal. |
| U9 | any user | to know how fresh the data is | Every answer and every screen shows the data's as-of date and that it is sample data. |
| U10 | two-part asker | sailings and a document question in one message | Both parts are answered separately, each with its own citations; a failure of one part does not hide the other. |

Reading conventions (also used to label the test questions): weeks run Monday to Sunday;
"next N days" is today to today+N; a month name is the whole month; "after X" and "from X"
include X; "before X" excludes X; "by X" includes X.

## 5. Information architecture

```
Schedule Assistant
|- Find sailings            form: from, to, departure window, direct only
|   |- Result list          ETD/ETA, carrier and vessel, transit days, routing, CY cut-off
|   `- Sailing detail       deadline timeline, routing, data status, source record
|- Ask a question           suggested questions, free text
|   |- Answer               one block per part; citation chips; answered / not answered label
|   |- Source of this answer   how the question was read + retrieved records
|   `- Feedback             helpful / not helpful
`- Persistent banner        sample-data and as-of notice
```

Data objects: **Sailing** (id, carrier, service, vessel, voyage, origin, destination, ETD,
ETA, transit days, routing, transshipment port, three cut-offs), **Port** (code, name,
aliases), **FAQ entry** (id, topic, answer), **Query** (intent, ports, dates, filters),
**Answer part** (text, cited record ids, value, or refusal reason).

Pipeline: question -> parser (rules; optionally a local LLM that only fills the Query) ->
validation -> retrieval -> templated composition -> grounding guard -> answer or refusal.
The model never writes answer text.

## 6. Success metrics and how each would be measured

Offline, measurable now (see README for current values):

| Metric | Definition | Measured by |
|--------|------------|-------------|
| Execution accuracy | Share of answerable test questions whose retrieved records and value exactly match an independently computed expected answer | `scripts/run_eval.py` against `eval/expected.json`; reported per question set, with the blind sets as the honest number |
| Refusal correctness | Share of should-refuse questions refused with the right reason | same script |
| Wrong answers given | Answerable questions answered (not refused) with a non-matching result - the costly error | same script; tracked as a count, target zero |
| Ungrounded answers | Answers containing a date, number or port not present in retrieved records | harness-side check in `run_eval.py`, separate from the runtime guard; target zero |

Online, for a pilot (not measured in this project - there are no users):

| Metric | Definition | Instrumentation | First target to validate |
|--------|------------|-----------------|--------------------------|
| Answer rate | Answered questions / all in-scope questions | Log each part's outcome and refusal reason | Set after two weeks of baseline |
| Source-view rate | Sessions that open "source of this answer" | Click event | A leading indicator of trust, no target |
| Helpful rate | Helpful / (helpful + not helpful) | Feedback buttons | Compare question types, not an absolute |
| Reported wrong answers | Answers a user or agent flags as wrong, per 1,000 answers | "Not helpful" plus a reason; weekly human review of a sample | The guardrail metric: any confirmed wrong date stops rollout |
| Deflection | Share of schedule/document contacts resolved without an agent | Compare contact volume for pilot vs control customers | Needs customer-service data |
| Time to answer | Median seconds from question to answer shown | Client timing | Faster than the form flow for cut-off questions |
| Unanswered-question backlog | Top refused or misread question patterns per week | Refusal log clustered by reason | Drives the next parser/FAQ iteration |

## 7. Risks

| Risk | Why it matters | Mitigation in this design | Residual |
|------|----------------|---------------------------|----------|
| **Hallucinated schedules** | A fluent invented sailing or cut-off is acted on | Answers are templates filled from retrieved rows; the LLM (if used) only produces a validated query; per-line grounding guard; refusal on empty retrieval | A misread question can still return real rows for the wrong lane or filter. The guard cannot see that. This is the main open risk and is what "wrong answers given" tracks. |
| **Liability** | A shipper misses a cut-off and holds the provider responsible | Every answer carries source, as-of date and "confirm with the carrier"; no predictions; booking actions out of scope; refusals are logged | Wording and terms need legal review before any real use; a disclaimer does not remove a duty of care |
| **Stale data** | Schedules change daily; yesterday's cut-off is wrong today | As-of date on every answer; "next sailing" never looks before today | The demo does not hide a sailing whose cut-off has already passed; a real feed needs per-record freshness and an expiry rule |
| Ambiguous language | "by Friday" could be departure or arrival; "next week" differs by locale | Written conventions; the source view shows how the question was read | Users will not read conventions; needs a confirm-the-reading step for date-sensitive answers |
| Parser brittleness | Rules pass their author's questions and miss other people's phrasing | Blind question sets written without access to the parser; first-run numbers kept | Rule coverage will always trail real phrasing; see roadmap |
| Missing or partial feed data | A carrier may not publish cut-offs (S12) | Refuse per field, do not estimate | Partial answers need a clear "not provided by carrier" state |
| Over-trust in the FAQ | General guidance read as carrier policy | FAQ answers are authored, cited by ID, and say to confirm | Needs owner and review date per entry |
| Prompt injection via the question | A question tries to change behaviour | No free-text generation; query fields validated against allow-lists | Low for this architecture |

## 8. Phased roadmap

| Phase | Goal | Contents | Exit criterion |
|-------|------|----------|----------------|
| 0 - done here | Prove the grounded-answer loop on sample data | Sample dataset, FAQ, rule parser, guard, evaluation with blind sets, clickable prototype | Zero ungrounded answers; honest baseline for accuracy |
| 1 - parsing quality | Raise blind-set accuracy without losing grounding | LLM-as-parser behind the same validation; "is this what you meant?" confirmation for date-sensitive questions; a third blind set per iteration | Blind execution accuracy and wrong-answer count agreed with stakeholders before pilot |
| 2 - real data, one carrier or one feed | Replace the sample with a schedule feed in the common API shape (S9, S10) | Ingestion, per-record freshness, "not provided" states, expiry of passed cut-offs, port master data | Data-quality report: coverage of cut-offs per lane; staleness under an agreed limit |
| 3 - assisted pilot | Customer-service agents use it first, customers second | Feedback capture, weekly review of flagged answers, refusal backlog | No confirmed wrong date in the pilot period; helpful rate and deflection measured against control |
| 4 - breadth | More languages, more carriers, hand-off to booking | Multi-carrier comparison, saved lanes and cut-off reminders | Decided from pilot data |

Each phase is gated by measurement from the one before; the order puts trust (grounding,
freshness) ahead of breadth.

## 9. Open questions

- Should "next sailing" skip a sailing whose cut-off has already passed? Probably yes for
  shippers, no for an agent checking a rolled container.
- Is a confirmation step acceptable friction for forwarders who type terse queries?
- Who owns FAQ content and its review cycle?
