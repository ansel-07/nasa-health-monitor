<!-- AI-assisted: generated with Claude Code and reviewed by Fran (review pending). -->

# Code review: possible improvements and things to change

Whole-repository review at commit `a035c27` (`main`, Saturday night after v1). **Nothing was
changed**: this file only documents findings so each owner can decide. Internal team document:
delete or keep out of the submission like the other working notes in `docs/`.

- **Scope:** `app.py`, `pages/` (6 screens), `core/` (11 modules), `scripts/` (2), `config/`
  (structure and consistency, not medical correctness), `tests/` (37 files), repo setup.
- **Method:** every source file read in full; the real configuration analysed with a script;
  "Advance mission 24 h" and Trends profiled on a temporary copy of `data/seed/`; the live-demo
  path of `AGENTS.md` 15 replayed with Streamlit's `AppTest`.
- **Not reviewed:** medical correctness of thresholds, symptoms, protocols and sources (Edu),
  and the visual result in a real browser (no browser available; items marked *verify*).

## How to read this

Each finding has an id, a severity, the owner of the file (`AGENTS.md` 4) and a suggestion.

| Severity | Meaning |
|---|---|
| **High** | Affects the live demo, the judges' experience or correctness today |
| **Medium** | Real problem or risk, but with a workaround or lower impact |
| **Low** | Robustness, clarity or maintenance |
| **Info** | Observation; no action needed now |

Ownership rules still apply: a finding in someone else's file is a request for that owner
(`AGENTS.md` 14), never a licence to edit it. "Contract" means `AGENTS.md` sections 5-7 (Ansel).

## 1. Summary: what matters most

1. **"Advance mission 24 h" is slow because every step re-reads the same files** (PERF-1 to
   PERF-5). Measured: 7.1 s, 537 CSV parses and 799 JSON loads for 42 rows. Caching the parsed
   measurements and the config by file modification time should bring it under 1-2 s **without
   changing any contract or detection result**. This is P0 task 1 of `docs/TONIGHT_HANDOFF.md`.
2. **Trends renders all 14 charts on every rerun** (PERF-6, PERF-7): 2.5 s, 90 CSV parses,
   627 JSON loads.
3. **The Main Menu does not catch errors from "Advance mission 24 h"** (BUG-1): a detection
   error shows a raw traceback in the live demo.
4. **The voice re-reads the same sentence on every rerun** (BUG-2).
5. **Tables built with `st.dataframe` leave a floating selection** (#143); the same widget is
   used in Trends and in "Waiting alerts" (BUG-3).
6. **Internal ids and raw values reach the astronaut** in Check-in (`watch`, `not_present`,
   `peripapillary_trt_left`) and dates use four different formats (UX-1, UX-2).
7. **Chart and flowchart colours were chosen for a light surface; the app is now dark**
   (UX-3, UX-4): the "Now" line and the visited-step green have low contrast. *Verify.*
8. **27 files still say "human review pending"** in their AI header (DOC-1): NASA asks for
   human review of AI-generated code.
9. **No test checks that the committed `data/seed/` equals what the generator produces**
   (TEST-1), and a test without path redirection can still write to the real `data/` (TEST-8).
10. **Dependencies are unpinned except Streamlit, and there is no CI** (DOC-5, DOC-7).

## 2. Measurements

Laptop, Windows, Python 3.12, temporary copy of the 14-indicator seed (1008 rows).

| Operation | Time | CSV parses | JSON loads | Notes |
|---|---:|---:|---:|---|
| `mission.advance_and_detect(24, "mars")`, 42 rows | 7.08 s | 537 | 799 | 8-10 s on the deployed app (`TONIGHT_HANDOFF.md`) |
| of which `data.get_baseline()` | 4.85 s | 451 calls | – | 68% of the total |
| of which `triggers.evaluate()` | 5.65 s | – | – | 1632 `conditions.check()` calls |
| Trends: 14 cards (chart + baseline + z each) | 2.54 s | 90 | 627 | on **every** rerun of the page |
| One compact chart (Check-in) | 0.11 s | 3 | 15 | |
| Full test suite | 70-100 s | – | – | same root cause |

## 3. Performance

**PERF-1 · High · Fran · `core/data.py:38-63, 100-132`**
`load_measurements()` parses the whole CSV on every call, and `get_baseline()`, `z_score()` and
`latest_values()` each call it again. In one Advance the file is parsed 537 times although it
changes only when a manual or protocol row is appended.
*Suggestion:* keep the parsed DataFrame in a module-level cache keyed by
`(path, st_mtime_ns, st_size)` and filter a copy; cache baselines the same way (they are
"frozen by construction", `AGENTS.md` 5.2). Invalidate in `add_measurement()` and
`reset_demo()`. No signature changes. Expected: Advance well under 2 s.

**PERF-2 · High · Ansel · `core/config.py:24-68`**
Every `load_*()` re-reads and re-parses its JSON file (docstring: "no cache, so edits show up
when Streamlit reruns"). 799 loads in one Advance; `problems.json` is the largest file.
*Suggestion:* cache in `_read_json()` by `(path, st_mtime_ns)`: edits still show up on the next
rerun, and callers get a deep copy or a read-only view so nobody mutates the cached object.

**PERF-3 · Medium · Juan Carlos · `core/triggers.py:34-113, 179-255`, `core/conditions.py:205-217`**
`evaluate()` re-validates the whole problem for every measurement (`_validate_symptom_problem`
runs `conditions.check(rule, {})` on every rule), then evaluates the rules in
`_symptom_levels()`, again in `_supports_symptom_alert()` and again recursively in
`_condition_evidence()`. `conditions.check()` also validates the condition tree on every call.
*Suggestion:* validate a problem once per configuration load; compute the symptom levels once
per measurement and reuse them; pass baselines in `ctx` (for example `ctx["baselines"]`) so a
leaf never triggers file access. Results must stay identical (existing tests cover it).

**PERF-4 · Medium · Juan Carlos · `core/episodes.py:59-66, 203-236`**
`_save_measurement_once()` loads the measurements and scans them row by row for each
measurement; `on_new_measurement()` reads `episodes.json` twice (`load_episodes`,
`load_pending`) and may write it twice (`save_episode`, `save_pending`).
*Suggestion:* one read and one write of the episodes file per measurement; the duplicate check
becomes cheap once PERF-1 exists.

**PERF-5 · Medium · Fran · `core/mission.py:115-138`**
`_mark_processed()` reads and rewrites `mission_state.json` after every processed row (42 reads
and 42 writes per Advance, each write containing the rest of the batch).
*Suggestion:* keep the pending list in memory and write it only when detection raises and once
at the end. The guarantee of #77 (nothing skipped after a detection error) is preserved; only a
process kill in the middle of a batch would re-send rows, which is already safe (idempotent).

**PERF-6 · Medium · Fran · `core/charts.py:191-194, 230, 266, 280`**
`_mission_day()` calls `config.load_mission()` for every point, mark and line: 627 JSON loads to
draw Trends.
*Suggestion:* read the mission start once per chart and pass it down.

**PERF-7 · Medium · Fran · `core/charts.py:206-218`, `pages/3_Trends.py:42-70`**
One chart parses the CSV three times (`load_measurements`, `get_baseline`, and `get_baseline`
again inside `threshold_bands`). Trends adds two more per card and builds all 14 charts even
when their expanders are closed, on every rerun.
*Suggestion:* pass the baseline into `threshold_bands()`; in Trends, build a chart only when its
card is open (a toggle or button with session state, or `st.fragment`) so a closed card costs
nothing.

**PERF-8 · Low · Fran · `core/activity.py:87-147`**
`bar_level()` reads the config, `activity.json`, the clock and the issues config for each card
(9 check-ins, 2 tutorials). *Suggestion:* a batch function (for example
`bar_levels(astronaut, kind) -> dict`), which is a contract addition (Ansel), or rely on PERF-2.

**PERF-9 · Low · Javi · `pages/4_Tutorials.py:22-43`**
`available()` runs the engine (`practice_episode` + `submit` + `current_step`) for every
protocol on every render, and `bar_level()` is computed twice per card (once directly, once in
`can_repeat_tutorial`). *Suggestion:* compute the level once and derive the gate from it.

**PERF-10 · Low · Juan Carlos · `pages/1_Check_in.py:228-231, 368-369`**
`triggers.assessment_issues()` runs once per field on every render and again after a submit.

**PERF-11 · Low · Ansel · `pages/5_Menu.py:66-71`**
No spinner while Advance runs (8-10 s on the deployed app): the screen looks frozen.
*Suggestion:* `with st.spinner("Advancing mission time…")`.

## 4. Correctness and robustness

**BUG-1 · High · Ansel · `pages/5_Menu.py:66-79`**
`mission.advance_and_detect()` and `data.reset_demo()` are called without `try/except`.
`advance_and_detect()` is designed to raise on a detection error (#77), so the Main Menu would
show a Streamlit traceback. Check-in catches `(ValueError, KeyError, OSError)` for the same call.
*Suggestion:* catch them, show one sentence, and mention that the unprocessed rows are retried
on the next advance (`result["recovered"]` is never shown either).

**BUG-2 · Medium · Ansel · `core/mascot.py:80-93, 97-100`**
With Voice on, every rerun re-creates the iframe and speaks the text again (`synth.cancel()`
then `speak`), even when the sentence did not change: any click on the page repeats it.
*Suggestion:* remember the last spoken text (for example in the parent window or
`sessionStorage`) and speak only when it changes.

**BUG-3 · Medium · Juan Carlos, Fran · `pages/1_Check_in.py:255, 394`, `pages/3_Trends.py:121, 141`**
Issue #143 (the selection of "Symptoms at last detection" floats when scrolling) comes from the
interactive grid of `st.dataframe`. The same widget is used for "Waiting alerts" in Check-in and
for "Alert history" and "Waiting alerts" in Trends. *Suggestion:* use `st.table` (read-only)
in all four places; nothing there needs selecting or sorting.

**BUG-4 · Medium · Fran (API), Juan Carlos, Javi (UI) · `core/activity.py:129-147`, `pages/1_Check_in.py:189`, `pages/4_Tutorials.py:41`**
A bar at 0 means both "never completed" and "completed long ago"; the spec asks for "Not
completed yet" in the first case. Check-in shows "Activity recency: 0%" and Tutorials
"Review bar: 0% (due)" for both. *Suggestion:* expose the last completion time (contract
addition) so the pages can tell the two cases apart.

**BUG-5 · Medium · Javi · `pages/4_Tutorials.py:55-64`**
`activity.complete()` is outside the `try`: a storage error at the end of a tutorial shows a
traceback after the astronaut finished it.

**BUG-6 · Medium · Ansel · `pages/5_Menu.py:72-79`**
Reset demo only deletes session keys starting with `check_in_`. `tutorial_run` (an in-memory
practice episode), `tutorial_whole` and `protocol_whole_*` survive the reset.
*Suggestion:* clear every page key, or keep an allow-list (astronaut, environment, voice).

**BUG-7 · Medium · Ansel · `core/config.py:191-209, 337`**
`validate_all()` reads each protocol with an unguarded `_read_json(path)`: a protocol with
invalid JSON ends `python -m core.config` with a traceback instead of an error line.
`validate_protocol()` also assumes every node is a dict (`node.get`).

**BUG-8 · Low · Fran · `core/data.py:66-97`**
`add_measurement()` accepts NaN and infinity (`float("nan")` passes), any astronaut id, any
unit, and a timestamp that cannot be parsed; extra keys are dropped silently. The callers
validate today, but the storage layer is the last line of defence.

**BUG-9 · Low · Fran, Juan Carlos · `core/data.py:186-192`, `core/episodes.py:69-73`**
With several open episodes for one astronaut, `data.get_open_episode()` returns the last one
and `episodes._open()` raises "repair the stored state first". The UI has no repair path other
than Reset demo. *Suggestion:* one behaviour, decided once (contract).

**BUG-10 · Low · Fran · `core/data.py:135-144`, `core/mission.py:33-44`, `core/activity.py:37-44`**
A corrupted JSON data file raises `JSONDecodeError` up to the page. Writes are atomic, so this
needs an external cause, but the message would be a traceback. *Suggestion:* a clear error that
offers Reset demo.

**BUG-11 · Low · Juan Carlos · `core/episodes.py:229-235`**
`on_new_measurement()` saves the measurement, the episode and the pending list in three
separate writes; a failure between them leaves a partial state. Replays are idempotent, so the
recovery of #77 repairs it, but only if the row is replayed.

**BUG-12 · Low · Javi · `core/protocol_engine.py:199-229`**
A protocol measurement is stored (through `on_new_measurement`) before the episode is saved at
the end of `submit()`. If a later automatic node raises, the measurement exists but the episode
did not advance. Real protocols have no `measure` node today, so it is latent.

**BUG-13 · Low · Javi · `core/protocol_engine.py:291-313`**
`_condition_label()` formats thresholds with `:g`, which raises on a non-numeric value, and it
ignores `metric`: `{"metric": "baseline_fraction", "below": 0.8}` is drawn as "Indicator < 0.8".
`flowchart_dot()` does not call `_require_complete()` first.

**BUG-14 · Low · Juan Carlos · `core/episodes.py:295-334`**
Pending items do not store the environment; `accept_pending()` uses the current one. Changing
the mission on Welcome between detection and acceptance changes which rules apply
(documented behaviour, but a contract decision: section 5.4).

**BUG-15 · Low · Fran · `core/activity.py:173-212`**
Resolving an issue and reporting it again starts a new record, so the persistence count
restarts from one day. Reasonable, but it is a product decision nobody has confirmed.
Persistence counts distinct days, not consecutive ones (`AGENTS.md` 5.6 wins over the spec).

**BUG-16 · Low · Fran · `core/mission.py:98-112`**
`advance()` stores the revealed rows as "unprocessed" even when the caller runs detection
itself; the next `advance_and_detect()` then reports them as `recovered`. Only tests and the
sandbox call `advance()` directly today.

**BUG-17 · Low · Ansel · `core/models.py:146-153`**
`severity_rank()` and `max_severity()` only know the legacy `SEVERITIES`: `severity_rank("watch")`
raises `ValueError`. `episodes._priority()` works around it. The contract lists them without
that limit.

**BUG-18 · Low · Ansel · `core/mascot.py:83`**
The text is embedded in a `<script>` with `json.dumps()`, which does not escape `</script>`.
The texts come from `config/`, so the risk is low; escaping `</` closes it.

**BUG-19 · Low · Fran · `core/mission.py:98-112`**
The clock has no end: after the last simulated day, Advance reveals nothing and says
"0 new simulated measurement(s)" forever. *Suggestion:* tell the user the simulated data is
over.

**BUG-20 · Low · Juan Carlos · `pages/1_Check_in.py:375-382`**
Confirming a repeat of one indicator completes the whole check-in (its bar goes to 100) even if
the other indicators of the group were not measured.

**BUG-21 · Low · Juan Carlos · `pages/1_Check_in.py:308-321`**
"Simulate wait" advances at least one hour (for a 2 or 10 minute wait) and runs detection for
every astronaut; from some times it crosses 08:00 and reveals the next day's rows.

**BUG-22 · Low · Juan Carlos, Edu · `pages/1_Check_in.py:336-349`, `pages/2_Protocol.py:163-171`**
Any finite number is accepted (the spec asks to validate input formats). A typo such as 3600 µm
opens an alert. Plausible ranges would be health content from Edu.

## 5. Demo and user experience

**UX-1 · Medium · Juan Carlos · `pages/1_Check_in.py:251-256, 395-397`, `core/triggers.py:142-149`**
Raw internal values are shown: "Problem state: watch", levels such as `not_present`, raw
severities in "Waiting alerts", and warnings like "Cannot evaluate peripapillary_trt_left".
Protocol, Tutorials and Trends already convert them ("Medical urgency").

**UX-2 · Medium · all page owners**
Four date formats: Check-in `2027-04-02T01:00:00`, Menu and Trends `2027-04-02 01:00 (day 2)`,
Protocol `02 Apr 2027, 01:00`, charts "Mission day". *Suggestion:* one helper (DUP-3).

**UX-3 · Medium · Fran · `core/charts.py:21-46`** *(verify on the deployed app)*
The palette was chosen for a light surface, and the app theme is now dark (`#111111`).
`NOW_COLOR = "#52514e"` (the "Now" line) is close to the background; `BASELINE_COLOR` and
`MISSION_COLOR` are borderline. *Suggestion:* use the dark-surface steps of the same palette.

**UX-4 · Medium · Javi · `core/protocol_engine.py:251, 380-398`** *(verify)*
The flowchart uses light fills with a transparent background: the visited green (`#15803d`) on
edges, edge labels and the "earlier steps" box has low contrast on the dark theme.

**UX-5 · Low · Ansel, Javi · `app.py:11`, `pages/2_Protocol.py:89`**
The browser tab says "Astronaut Health Monitor" while the product is "SpaceDoc"; the screen
title is "Protocol" and the navigation title "Protocols".

**UX-6 · Low · all page owners**
Opening a page without an astronaut behaves differently: Menu and Tutorials redirect to
Welcome, Check-in and Protocol show a message (Protocol with a link), Trends shows a warning
with no link (`pages/3_Trends.py:17-19`).

**UX-7 · Low · Ansel · `core/mascot.py:27, 66`**
`MASCOT_NAME = "TODO: mascot name"` is read by screen readers (`aria-label`).

**UX-8 · Low · Edu · `config/protocols/*.json`**
Six steps (three per protocol) have more than 200 characters, up to 271; the mascot reads every
step aloud (`AGENTS.md` 15: one or two short sentences).

**UX-9 · Low · Juan Carlos, Javi, Edu**
The live path is about 9 clicks and needs typing "360" (`AGENTS.md` 15: no typed values, about
6 actions). Already in `TONIGHT_HANDOFF.md`.

**UX-10 · Low · Ansel · `pages/0_Home.py:51-55`**
"Try it in 1 minute" hard-codes the story and the value 360 µm. It must change together with
`scripts/generate_data.py` and `docs/DEMO_DATA_HANDOFF.md`.

**UX-11 · Info · Gonzalo, Edu · `config/checkins.json`**
Check-in bars now last 168 to 720 hours, so one 24 h advance moves them at most one step: the
live demo cannot show a bar draining.

**UX-12 · Low · Fran · `core/charts.py:245-262`**
Several bands put their labels in the same corner ("top right"), and "Your baseline" can
collide with "Launch". Long indicator names make long card titles in Trends.

**UX-13 · Info · Fran · `core/charts.py:68-108`**
Compound rules (`all` / `any` / `count_at_least`) draw no band. Today that is 1 of 24 level
rules (in `muscle_atrophy`).

**UX-14 · Info · Javi**
The mascot mood is always "neutral" in Protocol, also at medical urgency.

**UX-15 · Info · Edu · `config/indicators.json`**
Six old indicators (blood pressure, glucose, heart rate, sleep, temperature) belong to no
problem and no check-in (#81).

## 6. Duplication and consistency

**DUP-1 · Low · Fran, Ansel** — The atomic "write to a temporary file, then replace" block exists
three times (`core/data.py:147-160`, `core/mission.py:51-67`, `core/activity.py:47-60`). One
helper (a new shared function needs Ansel's OK).

**DUP-2 · Low · all** — Small helpers copied: `readable` ×4 (Protocol, Tutorials, Trends, engine),
`_is_number` / `_finite` ×4, the "valid baseline" rule ×4 (`conditions._metric_value`,
`charts._valid_baseline`, Trends, the message in `triggers.assessment_issues`), and five
condition-tree walkers (`config._leaf_conditions`, `triggers._leaves`, `triggers._indicator_ids`,
`episodes._references`, tests).

**DUP-3 · Low · Fran, Ansel** — "Mission day" is computed in `pages/5_Menu.py:63`,
`pages/3_Trends.py:102` and `core/charts.py:191`. *Suggestion:* `mission.day(moment)` (contract).

**DUP-4 · Low · Javi** — Protocol and Tutorials render the same step types with copied code
(`pages/2_Protocol.py:143-179`, `pages/4_Tutorials.py:93-122`); `scripts/preview_protocol.py`
has a third flowchart renderer.

**DUP-5 · Low · Fran** — The CSV is parsed with the same options in `data.load_measurements()` and
`mission._revealed()`; the second exists only because the first hides future rows.

**DUP-6 · Low · Juan Carlos** — Private functions used across modules:
`conditions._is_number` and `conditions._metric_value` from `triggers` and `episodes`,
`triggers._symptom_levels` from `episodes`. Make them public or move them.

**DUP-7 · Low · page owners** — Two width APIs: `use_container_width=True` (Home, Menu, Protocol,
Tutorials: 12 uses) and `width="stretch"` (Check-in, Protocol, Tutorials: 12 uses).

**DUP-8 · Low · Ansel** — `pages/5_Menu.py:63` uses `__import__("datetime")` instead of an import.

**DUP-9 · Low · Juan Carlos** — `pages/1_Check_in.py` `main()` is about 290 lines with nested
closures, and `report()` uses `st.rerun()` as control flow (code after it never runs).
Splitting it into list, detail and confirmation functions would make it reviewable.

**DUP-10 · Info · Juan Carlos** — `load_problems()` already hides `_` fixtures; the extra filters in
`pages/1_Check_in.py:113` and `core/triggers.py:211` are redundant.

**DUP-11 · Info · all** — No real problem uses the legacy `triggers` format any more, but every
module still carries both paths (`TRANSITION`). Removal is future work in `TONIGHT_HANDOFF.md`.

## 7. Configuration validation (Ansel, `core/config.py`)

**VAL-1 · Low** — `count_at_least` is checked only at the top of a condition (`:107-111`), not
inside `all` / `any`; legacy triggers check only the top-level `indicator` (`:330-332`).

**VAL-2 · Low** — Protocols: a `question` may have empty `options`; a `decision` branch may lack
`if` or `next`; `wait_min` is not checked; a loop with no way out is found only at run time
("automatic cycle"); only "some end is reachable from start" is checked, not "every node can
reach an end".

**VAL-3 · Low** — `--strict` ignores `subjective_issues.json` (labels, questions, actions) and
`mission.json` (name).

**VAL-4 · Low** — `mission.json`: `start` is not parsed as a date and `astronauts` is not compared
with `data/seed/astronauts.csv`.

**VAL-5 · Low** — "Every indicator used by a real problem is in exactly one check-in"
(`AGENTS.md` 5.6): the validator rejects duplicates but not a missing indicator. Today the
configuration complies (checked by script).

## 8. Tests

**TEST-1 · Medium · Fran** — Nothing checks that the committed `data/seed/measurements.csv` and
`mission_state.json` equal the generator's output: the block and the seed can drift apart.
*Suggestion:* a test that generates into a temporary folder and compares with `data/seed/`.

**TEST-2 · Medium · Ansel** — `pages/5_Menu.py` has no test for Advance, Reset demo or their
errors (it only appears in `test_subjective_symptoms.py`).

**TEST-3 · Low · Fran, Juan Carlos** — No guard against the performance regression: a test that
counts file reads during one Advance would keep PERF-1 fixed.

**TEST-4 · Low · all** — Page tests mock heavily. One end-to-end test through `app.py` with the
real seed (Reset → Advance → Check-in → Simulate wait → repeat → Protocol → Trends) would
protect the live demo; the rehearsal script used for this review can become that test.

**TEST-5 · Info** — Tests that compared a whole result dictionary broke when a key was added
(#107, #115). Compare only the keys under test.

**TEST-6 · Info** — 37 files, about 900 collected tests, 70-100 s. PERF-1 and PERF-2 would
shorten it.

**TEST-7 · Low · Fran** — No test for corrupted data files (BUG-10) or for NaN / infinite values
in `add_measurement()` (BUG-8).

**TEST-8 · Medium · Ansel · `tests/conftest.py`** — A test that forgets to redirect a data path
writes to the real `data/` (it happened twice today with `mission_state.json`).
*Suggestion:* an autouse fixture that points every `models.*_FILE`, `DATA_DIR` and `SEED_DIR`
copy to `tmp_path`, so it cannot happen.

## 9. Documentation, process and deployment

**DOC-1 · Medium · owners** — 27 files declare "human review pending" in their `AI-assisted`
header: `pages/1_Check_in.py`, `pages/2_Protocol.py`, `pages/4_Tutorials.py`,
`core/conditions.py`, `core/episodes.py`, `core/protocol_engine.py`,
`scripts/preview_protocol.py`, 19 test files and `docs/DEMO_DATA_HANDOFF.md`. NASA Space Apps
asks for AI-generated code to be acknowledged and reviewed by a person.

**DOC-2 · Low · Ansel · `AGENTS.md` 7** — Public functions missing from the contract:
`protocol_engine.practice_episode()` and `charts.threshold_bands()`. `core/models.py:130` says
optional node fields are in section 7 (they are in section 9). The `ctx` line in the
`core/conditions.py` docstring omits `symptoms` and `var_indicators`.

**DOC-3 · Medium · Ansel, Edu, Gonzalo · `README.md`** — Six `TODO` lines: slides, Space Apps page,
the mascot, indicators and sources, NASA resources, other data.

**DOC-4 · Low · Ansel · `docs/`** — Four Spanish documents (`ESTRUCTURA.md`, `WORKFLOW.md`,
`Preparación del entorno…`, `sintomas_subjetivos_atrofia_SANS.md`) to translate or delete
before the repository is public (already in `TONIGHT_HANDOFF.md` §5). This file too.

**DOC-5 · Medium · Ansel · `requirements.txt`** — Only Streamlit is pinned. pandas, plotly and
numpy float, so the deployed app can install other versions than the ones tested (locally:
pandas 3.1.1, plotly 7.1.0, numpy 2.5.4). There is no Python version file; the version is set
by hand in Streamlit Cloud. *Suggestion:* pin all five.

**DOC-6 · Low · Ansel** — No `.gitattributes`: on Windows the working copies mix CRLF and LF
(`data/mission_state.json` is CRLF, its seed copy LF), which produces noise in `git status` and
byte differences between identical files. *Suggestion:* `* text=auto eol=lf`.

**DOC-7 · Medium · Ansel** — No CI: `python -m pytest` and `python -m core.config` run only on
each person's laptop before a pull request. A small GitHub Actions workflow would check every
PR.

**DOC-8 · Low · Ansel · `.gitignore`** — Leftover temporary files from atomic writes
(`data/.episodes-*.tmp`, `.mission-*.tmp`, `.activity-*.tmp`) are not ignored.

**DOC-9 · Info · Fran, Ansel · `data/`** — `data/*.csv|json` duplicate `data/seed/` and are
tracked. The app only uses the seed (per-session copies); the duplicates exist for scripts and
tests and can drift.

**DOC-10 · Info · Ansel** — `components.html` is deprecated; Streamlit is pinned to 1.67.0
because of it (known, `TONIGHT_HANDOFF.md`).

**DOC-11 · Info · Javi** — `scripts/preview_protocol.py` is a developer sandbox (it patches core
functions with `unittest.mock`). Decide whether it stays in the public repository.

**DOC-12 · Info · Ansel** — `TONIGHT_HANDOFF.md` says `v1` is a git tag; `git ls-remote --tags
origin` returns none.

## 10. Notes per file

Minor points not listed above.

- **`app.py`** — The back button is a plain button above the title; fine. No page shows which
  astronaut and mission are active except Trends, Check-in and the Menu's demo controls.
- **`core/models.py`** — `SESSION_DATA` is a mutable module flag toggled by tests. Old session
  folders are removed only when a new session is created (fine). `_create_session_dir()` copies
  the seed atomically (good).
- **`core/config.py`** — `load_protocol()` raises `KeyError` for an unknown problem; callers
  catch it.
- **`core/data.py`** — `reset_demo()` leaves files that are not in the seed (documented); a new
  data file needs a seed copy or it is never reset. `extrasaction="ignore"` hides typos in keys.
- **`core/mission.py`** — `hours` is annotated `int` but any positive number is accepted
  (Check-in relies on it). `now()` reads the state file on every call (PERF-1 covers it).
- **`core/activity.py`** — `_full_duration()` accepts `_example` ids in the real app (harmless).
  With a `TODO` duration a bar stays at 0 even right after completion (documented choice).
- **`core/charts.py`** — `threshold_bands()` is public and tested but not in the contract
  (DOC-2). The y-range includes every band edge, so a far threshold compresses the data.
- **`core/conditions.py`** — `equals` accepts booleans and numbers, but answers are stored as
  strings: `{"answer": "x", "equals": true}` can never match.
- **`core/triggers.py`** — `symptom_levels()` raises `KeyError` for an unknown problem id.
- **`core/episodes.py`** — `_require_symptom_confirmation_data()` enumerates every combination
  of uncertain symptom levels (`itertools.product`); fine with 8 symptoms and few uncertain
  ones, exponential in the worst case.
- **`core/protocol_engine.py`** — `quote = lambda …` (`:375`); missing blank lines between the
  first functions. `_require_complete()` walks the whole protocol on every call.
- **`core/mascot.py`** — `frame_height()` estimates lines from characters; long texts can leave
  empty space or be cut. Voice is "not verified in every browser" (docstring).
- **`pages/0_Home.py`** — With an empty `astronauts.csv` the selector is empty and NEXT stays
  disabled, with no explanation.
- **`pages/5_Menu.py`** — `names[astronaut]` raises `KeyError` if the session astronaut is not
  in the file. No direct "Go to Check-in" after a new alert (the mascot says it).
- **`pages/1_Check_in.py`** — The bar colour is injected with CSS that depends on Streamlit's
  internal `data-testid` (works while Streamlit is pinned). Hard-coded colours for the bars.
- **`pages/2_Protocol.py`** — Errors are replaced by a generic sentence with no detail or log,
  which makes a live failure hard to diagnose.
- **`pages/3_Trends.py`** — No "back to Welcome" link when there is no astronaut (UX-6).
- **`pages/4_Tutorials.py`** — A practice run keeps the environment it started with if the
  mission is changed on Welcome.
- **`scripts/generate_data.py`** — One random stream for everything: adding or reordering an
  indicator changes every later value (documented by Edu). A stream per (astronaut, indicator)
  would make the data stable. The parameter block exists twice (script and document), kept in
  sync by a test.

## 11. Suggested order of work

Sunday, before the 13:00 integration and the 16:00 freeze:

1. **PERF-1, PERF-5, PERF-6, PERF-7** (Fran) and **PERF-2** (Ansel): the Advance and Trends
   speed-up, no contract change. Then **PERF-3, PERF-4** (Juan Carlos) if time allows.
2. **BUG-1, BUG-2, PERF-11** (Ansel): the Menu and the voice in the live demo.
3. **BUG-3, UX-1, UX-2** (Juan Carlos, Fran): tables and readable texts.
4. **UX-3, UX-4** (Fran, Javi): check colours on the dark theme in a browser.
5. **TEST-1, TEST-8** (Fran, Ansel): protect the seed and the real `data/`.
6. **DOC-1, DOC-3, DOC-5** (owners, Ansel): review headers, README, pinned versions.

Everything else can wait until after the freeze or be recorded as future work.
