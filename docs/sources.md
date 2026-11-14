# Sources

All pages are public and were retrieved on **2026-11-14**. Nothing behind a login was used.
Page text and tables are not copied; the notes below are my own summaries.

"How read" matters for how much weight a note can carry:

- **browser** - the rendered public page was opened and its visible text read directly.
- **summariser** - the page was fetched by an automated tool that returns a model-written
  summary, so the wording of the page itself was not inspected.
- **snippet** - only a search-result snippet was seen. Treated as unverified.

| ID | Page | URL | How read | What it supports |
|----|------|-----|----------|------------------|
| S1 | Maersk - schedules, point-to-point | https://www.maersk.com/schedules/point-to-point | browser | Public search page; switch between containers and boxes/pallets; form has a selector set to "departing" (its other options were not opened), a date and a container-type field. |
| S2 | MSC - search a schedule | https://www.msc.com/en/search-a-schedule | browser | Three search modes (point-to-point, vessel, arrivals/departures); the page also points to schedule APIs. |
| S3 | CMA CGM - schedules | https://www.cma-cgm.com/ebusiness/schedules | browser | Origin, destination, a "search on" selector set to departure (other options not opened), date and a period of up to ten weeks; results assume a standard 40-foot dry container unless cargo details are changed. |
| S4 | ONE - point-to-point schedule | https://ecomm.one-line.com/one-ecom/schedule/point-to-point-schedule | browser | Tabs for point-to-point, vessel, port and long-range schedules; list and calendar views; default window of the next two weeks; cargo type; the page frames schedule search as the entry to booking. |
| S5 | Evergreen ShipmentLink - sailing schedules by point | https://www.shipmentlink.com/tvs2/jsp/TVS2_InteractiveSchedule.jsp | browser | Origin, destination, "departure on/after", optional "arrival before", duration of one to four weeks, reefer or non-reefer. |
| S6 | COSCO SHIPPING Lines - SynConHub | https://synconhub.coscoshipping.com/ | browser (Chinese page) | Home page lists instant quotes, instant booking that returns a booking number, self-service documents, value-added service coupons, trucking, customs service and online payment; login or registration is offered. |
| S7 | Maersk - Captain Peter | https://www.maersk.com/digital-services/captain-peter | browser | A named assistant for reefer cargo visibility, sold in three packages; it is not a schedule or booking assistant. |
| S8 | Seatrade Maritime News, 8 May 2023 - OOCL AI chatbot | https://www.seatrade-maritime.com/containers/oocl-launches-ai-chatbot-for-customers | browser | Press report: a chatbot on three OOCL customer platforms answers questions on schedules, product information and cargo tracking; first in simplified Chinese; built on a cloud vendor's model. |
| S9 | DCSA - Commercial Schedules standard | https://dcsa.org/standards/commercial-schedules | summariser | The standard defines three ways to obtain schedules: point-to-point routings, port schedules and vessel schedules. |
| S10 | DCSA press release, 24 Sep 2024 - Commercial Schedules 1.0 final | https://dcsa.org/newsroom/dcsa-releases-final-version-of-commercial-schedules-1.0-standard | summariser | Version 1.0 is final; it can carry estimated cut-off dates and times. |
| S11 | DCSA - explainer on the Commercial Schedules standard | https://dcsa.org/newsroom/commercial-schedules-standard-explainer | summariser | States the shipper pain (log in to each carrier portal, search and compare by hand) and says the standard is live with nine carriers. |
| S12 | project44 developer guide - point-to-point schedules | https://developers.project44.com/guides/shippers/visibility/ocean/sailing-schedules/point-to-point-schedules | summariser | A multi-carrier schedule API whose response follows DCSA Commercial Schedules 1.0; cut-offs are present only when the carrier supplies them. |
| S13 | Freightos - home page | https://www.freightos.com/ | summariser | Marketplace positioning: compare rates from several providers, book online, track shipments in one dashboard. |
| S14 | Air Freight News, 23 Sep 2025 - "Ask Fluent" launch | https://airfreight.news/articles/full/fluent-cargo-launches-ask-fluent-the-chatgpt-for-live-cargo-logistics | summariser | Press release: a conversational search over a schedule/routing data platform, available to existing customers. |

## Could not verify

| ID | Page | URL | What happened |
|----|------|-----|---------------|
| U1 | Hapag-Lloyd - interactive schedule | https://www.hapag-lloyd.com/en/online-business/schedule/interactive-schedule.html | Automated-browser check page (HTTP 403). Not bypassed. Nothing about this product is claimed. |
| U2 | OOCL - sailing schedule | https://www.oocl.com/eng/ourservices/eservices/sailingschedule/Pages/default.aspx | Same (HTTP 403). The only OOCL statement in this repo comes from the press report S8. |
| U3 | Supply Chain 24/7 - Flexport and AI assistants | https://www.supplychain247.com/article/flexport-ai-assistants-freight-booking-tracking | Page blocked (HTTP 403); only a search snippet was seen. Mentioned in the analysis as unverified. |

Other limits of this research:

- No search was actually run on any carrier site, so **result fields** (for example whether
  each carrier shows cut-offs in its result list) are not verified. Statements are limited to
  what the search form and the page text show.
- S8 is from 2023; whether that chatbot still exists, or now has an English version, was not checked.
- The "nine carriers" figure in S11 is the standards body's own statement; the page does not name them.
- S9-S14 were read through a summariser, so fine wording was not inspected.
- Products behind a login (booking flows, account dashboards) were not looked at.
- Whether any carrier currently offers an LLM-based schedule assistant in English was **not established**
  either way; absence of evidence here is not evidence of absence.
