# Landscape and competitor analysis

Scope: public digital products a shipper meets when asking "what sails from A to B, how long
does it take, when are the cut-offs, what do I need to book". Source IDs (S1...) and the
things I could not verify (U1...) are listed in [sources.md](sources.md), retrieved 2026-11-14.
This is desk research on public pages by one person; no interviews and no logged-in flows.

## 1. Four kinds of product

| Kind | Examples looked at | What the shipper gets | Limits seen from the public side |
|------|--------------------|-----------------------|----------------------------------|
| Carrier schedule search | Maersk (S1), MSC (S2), CMA CGM (S3), ONE (S4), Evergreen (S5) | A form: origin, destination, date window; some add cargo or container type | One carrier per site; every form is laid out differently; the user must already know port names and the carrier's vocabulary |
| Carrier e-commerce / booking | COSCO SynConHub (S6); ONE frames schedule search as the first step of booking (S4) | Quote, book, documents and payment in one account | Behind registration; not inspected here |
| Multi-carrier data and marketplaces | Freightos (S13), project44 schedules API (S12), DCSA standard (S9-S11) | Comparison across providers, or one API shape for many carriers | Completeness depends on what each carrier supplies; cut-offs can be missing (S12) |
| Conversational assistants | OOCL chatbot (S8, press, 2023), "Ask Fluent" (S14, press, 2025), Maersk Captain Peter (S7, reefer visibility only) | Questions in plain language | Public pages say little about grounding, citations or refusal behaviour |

## 2. Schedule search forms compared

Only what the form itself shows; no searches were run, so result columns are not compared.

| | Maersk (S1) | MSC (S2) | CMA CGM (S3) | ONE (S4) | Evergreen (S5) |
|---|---|---|---|---|---|
| Point-to-point search without login | yes | yes | yes | yes | yes |
| Other schedule views on the same page | not seen | vessel; arrivals/departures | not seen | vessel; port; long range | not seen on this page |
| Date input | date plus a selector set to departing | not inspected | date, a selector set to departure, period in weeks (capped) | start date plus window | departure on/after, optional arrival before, duration in weeks |
| Cargo or equipment as an input | container type | not inspected | optional cargo details; a default container is assumed | cargo type | reefer or non-reefer |
| Natural-language input | none seen | none seen | none seen | none seen | none seen |

"Not seen" means the element was not in the page text I read, not that the carrier lacks it.
Hapag-Lloyd and OOCL schedule pages could not be opened by an automated browser (U1, U2).

## 3. What the landscape suggests

1. **Search is a solved form; the question is not.** All five carrier pages answer "from, to,
   when". None of the forms takes a question such as "what is the documentation cut-off of the
   next direct sailing" - the user has to run a search, open a result and read it off.
2. **Arrival-based planning is unevenly supported.** One form shows an explicit
   "arrival before" field (S5); two others have a departure selector whose alternatives I did
   not open (S1, S3). A shipper who thinks "it must be there by the 25th" often has to translate
   that into a departure window.
3. **Schedules and booking knowledge live in different places.** Schedule pages give dates;
   what to prepare for a booking sits in help pages or with customer service. S6 and S4 show
   carriers pulling schedule, booking and documents into one flow, but behind an account.
4. **Standardised data is arriving.** A common schedule API now exists, covers point-to-point
   routings and can carry cut-offs (S9, S10), and third parties already expose it (S12). That
   makes a carrier-neutral assistant technically plausible, and it also means cut-offs may be
   absent for some carriers (S12) - so the product must be able to say "not provided".
5. **Assistants exist, but trust features are not visible.** A carrier chatbot answering
   schedule questions was reported in 2023 (S8) and a data platform launched conversational
   search in 2025 (S14). A forwarder is reported to have opened booking to general AI assistants
   (U3, unverified). From public material I could not find how any of them shows the source of
   an answer or what they do when data is missing. That is the gap this project explores.

## 4. Positioning of this project

| Design choice | Why, given the above |
|---------------|----------------------|
| Question in, cited answer out; the form stays as an equal entry point | Finding 1: the form already works for simple searches |
| Every date, number and port must come from a retrieved record, checked before display | Finding 5; a wrong cut-off costs a rolled container |
| "Show the source of this answer" on every answer | Finding 5 |
| Refuse instead of guess: no data, unknown port, missing origin/destination, out of scope | Finding 4: real feeds have holes |
| Arrival-by questions are first-class | Finding 2 |
| Booking and document FAQ beside the schedule | Finding 3 |
| No rates, no tracking, no booking execution | Different data, different liability; see PRD non-goals |

## 5. What this analysis cannot tell you

- How often shippers actually ask these questions, and through which channel. That needs
  customer-service logs or interviews, which a personal project does not have.
- What logged-in portals do. Booking flows may already answer much of this for existing customers.
- Whether the gap in finding 5 is real or only invisible from outside.
