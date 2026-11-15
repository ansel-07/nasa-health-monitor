<!-- AI-assisted: written with Claude; human review by Edu pending. -->

# Protocol review report: SANS and muscle atrophy

2026-11-15. Covers `config/protocols/sans.json`,
`config/protocols/muscle_atrophy.json` and `PROTOCOL_FLOWCHARTS.md`, reviewed
against `guia_tratamientos_vigilancia_urgencia.pdf` (2026-11-14, SHA-256
`7570681f...eae700`) and the seven sources it cites.

**Not done.** Only the uploaded files were available, not the repository. So
`python -m core.config --strict`, `python -m pytest` and the Protocol screen
were not run, and `AGENTS.md` (the current technical reference according to
`ESTRUCTURA.md`) was not seen. Structure was checked against `ESTRUCTURA.md`
plus three constructs the existing protocol files already use outside it:
`source` on every node, the `symptom` + `level_is` condition, and the
`medical_urgency` severity.

## 1. Problems in the original protocols

**Branching points that did not change the action** (three per file):

- `u_env`: every environment led to a flight-surgeon contact followed by
  `u_handover` (three in muscle, two in SANS); only the wording differed. The
  muscle default branch could never be taken.
- `u_stop`: `Done` and `I can't` both led to a crew-medical-officer contact and
  then to the same step. The `I can't` route also skipped `u_local`, so the
  assessment instructions were never shown on it.
- `w_concern` (SANS) and `w_limits` (muscle): "priority" and "routine" led to
  two officer contacts followed by identical steps.

**Two further redundant steps:**

- `u_support` asked whether the clinician had requested Earth support. It was
  not derived from the guide (its own source note said so) and let the crew
  skip the Earth contact the guide directs on the ISS and on Mars.
- SANS `w_missing_data` was a second officer contact made while the astronaut
  was already reviewing results with the clinician.

**Escalation.** The ~98 % figure could not be reproduced on these files. A
flight-surgeon contact was on 8 of 16 SANS routes and 12 of 19 muscle routes
(57 % overall), always optional and identical in every environment. A crew
medical officer contact was on 100 %. The real defect was that the kind of
contact did not follow the clinical situation: Earth contact depended on an
optional answer instead of the guide's environment rule, and a priority review
looked the same as a routine notification.

**Tree design.**

- The first question was the only way into the urgent branch. A clinician could
  not escalate after a priority review, and insufficient optical correction (an
  urgency criterion in the guide) led nowhere.
- SANS optical correction was shown to everyone; the guide ties it to refractive
  change, and mild symptoms were never asked about.
- Guide content missing from the steps: check other causes, correct an energy
  deficit, no forced walking or exercise, sudden weakness is not assumed to be
  chronic atrophy, glasses do not replace assessment of a visual loss, EVA and
  demanding tasks suspended until the clinical decision.

## 2. Changes and why

| Change | Why | Evidence |
| --- | --- | --- |
| `u_env` has two outcomes that do different things: Moon -> `u_moon` (care on board, clinician evaluates transfer, no Earth contact); any other environment -> `u_earth` (one flight-surgeon contact). | The guide directs Earth contact in Earth orbit and on Mars and names none on the Moon. The contact card already shows each environment's delay, so separate ISS and Mars nodes added nothing. | PDF p. 1, "Aplicacion por entorno" [P]; sources [3], [7] |
| `u_support` removed. | See above: the guide's rule is directive, not optional. | PDF p. 1 |
| `u_stop` has one exit; `u_help` removed. | Both exits meant "activate the on-board medical lead", which `u_local` does; nothing is skipped any more. | PDF pp. 1-2, urgency: initial action |
| New `w_review_outcome` after `w_priority_review` (both files). | A priority review now differs from a routine notification: the episode waits for the clinician's outcome, and the clinician can declare an urgency. | PDF p. 2, "Hallazgo preocupante sin sintomas" [P]; p. 1, "valoracion prioritaria" |
| SANS: new `w_symptoms`; `w_correction` only when focusing or reading is harder; its `I can't` sets a medical urgency. | Optical correction is for refractive change; without symptoms the app must not invent a pathological state; correction needed beyond the available one is an urgency criterion. | PDF p. 2, watch activation and management, urgency activation [C], closing rules |
| SANS `w_missing_data` is an `info` step ("not evaluable") instead of a second contact. | The clinician is already involved; the guide asks for "not evaluable" to be shown. | PDF p. 2, closing rules |
| Step wording completed with the missing guide content listed in section 1. | Present in the guide, absent or weaker in the steps. | PDF pp. 1-2 |

Unchanged: both red-flag questions, the concern-level conditions, the handover
hold, the two end states, and the absence of thresholds, doses, waits and
`measure` nodes. Node IDs removed, added and retyped are listed at the end of
`PROTOCOL_FLOWCHARTS.md`.

## 3. Medical sources

Every node cites the PDF page and section it implements. The cited sources were
re-read on 2026-11-15:

- [1] NASA Exercise Overview: specialists build individual exercise
  prescriptions; the in-mission strength standard is 80 % of baseline.
- [2] NASA nutrition book (opening chapters): inadequate energy intake goes with
  lean-tissue loss; adequate energy and protein come first, supplements are not
  required.
- [3] NASA health-care FAQ: flight surgeons follow each crew during the mission;
  an emergency can mean return in the crew's own spacecraft.
- [4] CSA reconditioning page: confirms post-flight reconditioning, gives no
  detail on its components.
- [5] NASA OCHMO-MTB-001: prescription lenses of varying power fly with the
  crew; LBNP, thigh cuffs and B vitamins are under study; no medication is
  proven for SANS.
- [6] Gew et al. 2026, publisher page only: space-anticipation glasses are the
  only established measure. Table 2 could not be retrieved.
- [7] NASA Hazard: Distance From Earth: up to 20 minutes one-way delay at Mars;
  crews handle emergencies with minimal Earth support.

## 4. Validation results

| Check | SANS before | SANS after | Muscle before | Muscle after |
| --- | --- | --- | --- | --- |
| Fields, targets, outcomes, conditions, references | pass | pass | pass | pass |
| Nodes / contact nodes (officer + flight surgeon) | 19 / 5 + 2 | 19 / 3 + 1 | 19 / 4 + 3 | 17 / 3 + 1 |
| Unreachable nodes; nodes that cannot reach an end | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| Branches never taken in any environment | 0 | 0 | 1 | 0 |
| Cycles other than the handover hold | 0 | 0 | 0 | 0 |
| Branching points whose outcomes differ only in wording | 3 | 0 | 3 | 0 |
| Distinct routes | 16 | 18 | 19 | 11 |
| Routes ending `handed_over` / `monitoring` | 12 / 4 | 12 / 6 | 16 / 3 | 8 / 3 |
| Routes with a flight-surgeon contact | 8 (50 %) | 6 (33 %) | 12 (63 %) | 4 (36 %) |
| Urgent routes with that contact: ISS, Moon, Mars | 4 of 8 each | 6 of 6, 0 of 6, 6 of 6 | 4 of 8 each | 4 of 4, 0 of 4, 4 of 4 |
| Non-urgent routes with that contact | 0 | 0 | 0 | 0 |
| Routes with a crew-medical-officer contact | 100 % | 100 % | 100 % | 100 % |
| Steps shown on non-urgent routes | 5, 5, 6, 6 | 5, 5, 6, 6, 6, 7 | 4, 5, 5 | 5, 5, 6 |
| Urgent routes not ending `handed_over`, or the reverse | 0 | 0 | 0 | 0 |
| Diagram identical to JSON (nodes, shapes, edges, labels) | yes | yes | yes | yes |

A route is a distinct sequence of nodes; the ISS and Mars now share one. Counts
show how many ways through the tree exist, not how often each will occur.

**Is the distribution justified?**

- *Officer contact on every route:* yes. The guide's first action in both
  states is to inform the on-board health lead, and the protocols only run
  after a confirmed finding or an active urgency. It was not reduced.
- *Flight-surgeon contact:* now on every urgent route on the ISS and Mars, on
  no Moon route and on no watch route, as the guide's environment rule says.
  The overall share fell from 57 % to 34 % as a side effect, not as a target.
- *Most routes end `handed_over`* because several situations lead into the
  urgent branch (active urgency, red flags, clinician-declared urgency and, for
  SANS, insufficient correction) and each multiplies by environment.
- Two officer contacts on one route now occur only when a watch route later
  escalates to urgency.

**Thresholds and interventions.** No step text contains a number, dose, device
setting, wait or follow-up interval. The only interventions offered are the
guide's: supervised exercise and nutrition review, prescribed optical
correction, sleep and habitat procedures. LBNP, thigh cuffs, supplements and
drugs appear only as things not to start.

The checks were run with `tools/protocol_check.py` (standard library only,
supplied with this report; optional to keep).

## 5. Open items for human review

1. **Edu - Moon.** The guide names no Earth contact on the Moon, so urgent Moon
   routes have none; `u_moon` says the clinician decides whether to request it.
   The previous version offered it on request. Deleting the `moon` branch of
   `u_env` sends the Moon to `u_earth` too.
2. **Edu - environment rule for SANS.** Page 2 has no environment section; the
   p. 1 rule is applied to SANS because it is worded generally.
3. **Edu - muscle priority outcome.** "The clinician may escalate" is written on
   p. 2 for SANS findings; `w_review_outcome` applies it to muscle by analogy.
4. **Edu - 55 micrometres / Frisen 1.** In source [5] these are indications for
   a post-flight lumbar puncture. Their use as an in-flight priority-review
   trigger is the guide's proposal. Nothing was changed.
5. **Edu - criteria tagged [C].** Not verified against Table 2 of [6]. "Needed
   correction beyond the available" was not found in the text of [5] or [6]
   that could be read.
6. **Edu - concern levels.** The guide names only TRT change, Frisen grade and
   strength below 80 % of baseline. Concern levels for refraction, acuity and
   the other muscle indicators are defined outside these files and were not
   checked.
7. **Edu - who performs a priority review.** No source says. It stays with the
   crew medical officer; on the ISS the physicians following the crew are
   ground flight surgeons [3].
8. **Gonzalo - rehearsal.** The SANS watch route has a new question, and shows
   six steps instead of five when the astronaut reports focusing difficulty.
9. **Javi - engine.** `u_stop` no longer has `next_if_cannot`; `info` nodes now
   carry `source`; tests naming removed nodes need updating; run the strict
   validator and pytest.
