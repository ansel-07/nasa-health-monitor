<!-- AI-assisted: generated with Claude Code and reviewed by Fran. -->

# Code review, limited to tonight's tasks

Findings from a whole-repository review (commit `a035c27`), **kept only where they belong to a
task of [`TONIGHT_HANDOFF.md`](TONIGHT_HANDOFF.md)** and ordered like that file. Everything else
found by the review was left out on purpose: it is not on tonight's list. Ids are kept from the
full review so they can be traced (`git log -p docs/CODE_REVIEW.md` has the full version).

Nothing here changes code. Medical content is never decided here (`AGENTS.md` 11): items that
need it are marked **[Edu content]**, as in the handoff. Severity: **High** affects the live demo
or the judges today; **Medium** a real problem with a workaround; **Low** robustness or clarity.

## P0 · Task 1 — Make "Advance mission 24 h" fast

Measured on a laptop with a temporary copy of the 14-indicator seed: one advance took **3.2 s**
(8-10 s on the deployed app), with **537 parses of the measurements CSV** and about **760 JSON
loads** for 42 rows. The root cause is that every step re-reads the same files.

| Id | Sev. | Where (owner) | Finding | Suggestion | Status |
|---|---|---|---|---|---|
| PERF-1 | High | `core/data.py` `load_measurements`, `get_baseline` (Fran) | The CSV is parsed again on every call; `get_baseline` is called 451 times for 42 (astronaut, indicator) pairs (68% of the time). | Cache the parsed file by content and each baseline by (content, mission clock). No signature change. | **Done in #158**: 3.2 s → 0.5 s, 537 → 3 parses, results byte-identical. |
| PERF-5 | Medium | `core/mission.py` `_mark_processed` (Fran) | The clock file is read and rewritten after every processed row (42 writes). | Write once at the end, or at once on a detection error (keeps #77). | **Done in #158**. |
| PERF-2 | Medium | `core/config.py` `_read_json` (Ansel) | Every `load_*()` re-reads and re-parses its JSON: about 750 loads per advance remain after #158. | Cache by `(path, st_mtime_ns)` (edits still show up on rerun) and hand out copies. | Open. |
| PERF-3 | Medium | `core/triggers.py` `evaluate`, `core/conditions.py` `check` (Juan Carlos) | Each measurement re-validates the whole problem, then evaluates the same rules three times (`_symptom_levels`, `_supports_symptom_alert`, `_condition_evidence`); `check()` re-validates the tree on every call. | Validate once per configuration load; compute symptom levels once per measurement; pass baselines in `ctx`. Same results (tests cover it). | Open. |
| PERF-4 | Medium | `core/episodes.py` `on_new_measurement`, `_save_measurement_once` (Juan Carlos) | Per measurement: a row-by-row duplicate scan of the CSV, two reads and up to two writes of `episodes.json`. The handoff's "avoid rewriting `measurements.csv` per row" points here. | One read and one write of the episodes file per measurement; the duplicate scan is cheap once PERF-1 is merged. | Open. |
| BUG-11 | Low | `core/episodes.py:229-235` (Juan Carlos) | Measurement, episode and pending list are saved in three separate writes; a failure between them leaves a partial state (replays are idempotent, so #77 repairs it). | Keep in mind when batching writes for PERF-4. | Open. |
| BUG-1 | High | `pages/5_Menu.py:66-79` (Ansel) | "Advance mission 24 h" and "Reset demo" have no `try/except`; `advance_and_detect()` raises on a detection error (#77), so the Main Menu would show a traceback on stage. Check-in already catches `(ValueError, KeyError, OSError)`. | Catch them, show one sentence, and say the rows are retried on the next advance. | Open. |
| PERF-11 | Low | `pages/5_Menu.py:66-71` (Ansel) | No feedback while Advance runs: the screen looks frozen for seconds on the deployed app. | `with st.spinner("Advancing mission time…")`. | Open. |
| TEST-3 | Low | `tests/` (Fran, Juan Carlos) | Nothing would catch the slowness coming back. | A test that counts CSV parses during one advance of the real seed. | **Done in #158** (`tests/test_data_cache.py`, fails if the cache is disabled). |

Not measured yet: the time on the deployed app after #158 (expected 1-2 s from the local ratio).
#158 also speeds up Trends (`core/charts.py`), which is not a task of the handoff.

## P0 · Task 2 — Check-in texts with an active alarm

No finding from the review: it was done before the urgent alarms were merged (#146). Nothing to add
to the handoff's description.

## P0 · Task 3 — Mascot-first layout

Findings in the code that the layout task rewrites (`core/mascot.py`, `pages/`); the specification
is [`FRONTEND_MASCOT_LAYOUT.md`](FRONTEND_MASCOT_LAYOUT.md).

| Id | Sev. | Where (owner) | Finding | Suggestion | Status |
|---|---|---|---|---|---|
| BUG-2 | Medium | `core/mascot.py:80-100` (Ansel) | With Voice on, every rerun speaks the same sentence again (any click repeats it). | Covered by the layout spec (`mascot_last_text`: speak only a new line). | In task 3. |
| — | Low | `core/mascot.py:45-48` `frame_height` (Ansel) | The iframe height is estimated from the number of characters, so long texts can be cut or leave empty space. | The spec sets new face sizes; keep the subtitles from being cut. | In task 3. |
| BUG-18 | Low | `core/mascot.py:83` (Ansel) | The text goes into a `<script>` through `json.dumps()`, which does not escape `</script>`. Texts come from `config/`, so the risk is low. | Escape `</` (`.replace("</", "<\\/")`) while rewriting the HTML. | Open. |
| UX-6 | Low | `pages/` (all owners) | Opening a page without an astronaut behaves differently: Menu and Tutorials redirect to Welcome, Check-in and Protocol show a message, Trends shows a warning with no link. | Use one behaviour while the navigation of the new Welcome is built. | Open. |

## P1 · Task 4 — Subjective-symptom details [Edu content for wording]

The details (onset, trend, location, impact, intensity, context, notes) will be stored with each
report in `data/activity.json` (`core/activity.py`, Fran).

| Id | Sev. | Where (owner) | Finding | Suggestion | Status |
|---|---|---|---|---|---|
| BUG-15 | Low | `core/activity.py:173-212` (Fran) | Resolving an issue and reporting it again starts a new record, so persistence restarts at one day; persistence counts distinct days, not consecutive ones (`AGENTS.md` 5.6). Nobody has confirmed either as a product decision. | Decide it when the new fields are added (a product question for the morning, not a medical value). | Open. |
| — | Info | `core/activity.py` `report_issues` (Fran) | One report is kept per calendar day; a second report on the same day is dropped. With details, a later report the same day (for example a worse intensity) would be lost. | Keep the latest details of the day, or every report with its time. | Open. |

## P1 · Task 5 — Shorter protocol texts [Edu content]

| Id | Sev. | Where (owner) | Finding | Status |
|---|---|---|---|---|
| UX-8 | Low | `config/protocols/sans.json`, `muscle_atrophy.json` (Edu) | Six steps (three per protocol) are longer than 200 characters, up to 271; the mascot reads every step aloud. | Open, needs Edu's wording. |

## P1 · Task 6 — README

| Id | Sev. | Where (owner) | Finding | Status |
|---|---|---|---|---|
| DOC-3 | Medium | `README.md` (Ansel, Gonzalo) | Three `TODO` lines left on `main` (2718e72): slides link (line 13), Space Apps project page (line 14) and "Meet the mascot" (line 35). Indicators, sources, NASA resources and other data were filled in #155. | Open. |

## P1 · Task 7 — Mascot name and `components.html`

| Id | Sev. | Where (owner) | Finding | Status |
|---|---|---|---|---|
| UX-7 | Low | `core/mascot.py:27, 66` (Ansel) | `MASCOT_NAME = "TODO: mascot name"` is read by screen readers (`aria-label`). | Open. |
| DOC-10 | Info | `core/mascot.py`, `requirements.txt` (Ansel) | `components.html` is deprecated; Streamlit is pinned to 1.67.0 because of it. | Long term, as the handoff says. |

## P1 · Task 8 — Narrow screens

Not reviewed: no browser was available. Nothing to add.

## Section 6 — Before submission

| Id | Where (owner) | Finding | Status |
|---|---|---|---|
| DOC-4 | `docs/` (Ansel) | Four Spanish documents: `ESTRUCTURA.md`, `WORKFLOW.md`, `Preparación del entorno · NASA Space Apps 2026.md`, `sintomas_subjetivos_atrofia_SANS.md`. | Open, as the handoff lists. |
| DOC-3 | `README.md` | No `TODO` left; slides link (see task 6). | Open. |

## Suggested order for tonight

1. Merge #158, then **PERF-2** (Ansel's file) and **PERF-3 / PERF-4** (Juan Carlos's files) to finish task 1; measure on the deployed app.
2. **BUG-1 and PERF-11** together with task 1: the Advance button is the first click of the demo.
3. Task 2 as written in the handoff.
4. Task 3, folding in **BUG-18** and **UX-6** while the mascot and pages are rewritten.
