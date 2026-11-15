<!-- AI-assisted: generated with Claude Code and reviewed by Ansel. -->

# Tonight's handoff (after v1, Saturday 23:00 → 02:00)

Owner: Ansel. Written at the v1 cut-off for the coding agent that works tonight.
**Tonight one coding agent works alone on the repository: nobody else pushes, reviews or answers questions.** It opens and merges its own pull requests.
**Read `AGENTS.md` first** (at least sections 3-7, 10, 11 and 16); this file only lists what is left and how to do it safely.

## 1. Ground rules for tonight

- `v1` is a git tag on the commit that worked in the live rehearsal. If anything breaks, compare with it or go back to it.
- **Every merge to `main` goes live**: Streamlit Cloud redeploys the public app automatically. Keep `main` working at all times.
- Work in a branch per task (`<agent>/short-description`), open a pull request, then **merge it yourself** (squash) only after the self-review checklist below passes. Never `git push --force` to `main`, never rewrite history, never delete branches or tags you did not create.
- **If a merge breaks something, revert it at once** with `git revert` in a new PR (not a force push), then continue.
- **Never invent medical content**: thresholds, symptoms, intervals, protocol steps and sources come from Edu (`AGENTS.md` 11). Tasks marked **[Edu content]** below need his input; an agent may only prepare the structure and ask.
- Keep the contracts (`AGENTS.md` 7) and the per-session data rules (5.5). New public functions go into section 7.
- **Nobody can answer questions tonight, so decide like a senior engineer.**
  - **If one option is clearly better** (simpler, safer, consistent with `AGENTS.md` and the spec, easy to undo), **take it and carry on**; record it in one line in the night log ("decided X because Y").
  - **Leave it for the morning only if the decision is important for the team to make**: medical or health content (Edu), a product or demo choice the team cares about, a contract change that breaks other owners' code, or anything hard to undo. Then write it under "Decisions for the morning" (task, question, options, your recommendation) and move on to the next task.
- You may edit any owner's file tonight (nobody else is working), but keep the contracts of `AGENTS.md` 7; if you add a public function, document it there.

### Self-review checklist before merging your own PR

1. `python -m pytest` passes (full suite) and `python -m core.config --strict` says OK.
2. The live demo path still works: `python -m pytest tests/test_check_in_seed_integration.py tests/test_check_in_app_integration.py tests/test_home_navigation.py` passes, and the steps of section 4 behave the same.
3. No medical value, threshold, symptom, interval, protocol step or source was invented or changed without Edu's written content.
4. No secrets, no new libraries, no new top-level folders; every new file has the `AI-assisted` header; English only.
5. The PR description says what changed and how it was tested.
- Feature freeze: **Sunday 16:00**. Integrations: Sunday 13:00.

## 2. Working within a token budget (read this if you are a coding agent)

The usage limit resets at 02:00. Spend it on the hardest, most valuable task first.

- **One task at a time, in the order of section 5.** Finish, open the PR, then take the next one.
- **Tests:** while working, run only the tests of the files you touch (e.g. `python -m pytest tests/test_mission.py`). Run the full suite (about 1,000 tests, more than a minute) **once, before opening the PR**.
- **Do not read large files unless the task needs them:** `data/*.csv` (1,000+ rows), the long documents in `docs/`, long GitHub issues. Read only the sections of `AGENTS.md` you need.
- **No subagents.** There are no other people's PRs to review tonight.
- Mechanical tasks (README, texts, translations) do not need the strongest model; keep it for performance and logic.
- Check usage with `/usage` in Claude Code.

## 3. State at v1

Works end to end on the deployed app (https://nasa-health-monitor-jyjqxq9oyta7gece258ben.streamlit.app/):
Welcome → Main Menu → Check-in (9 grouped check-ins with bars, multi-field form, confirmation, 12 subjective symptoms and 4 urgent alarms) → Protocols (simplified SANS and muscle flows, focused flowchart, one-click answers, list by severity, Earth delay only for flight-surgeon contacts) · Trends (cards with inline charts) · Tutorials (practice mode, bars, gate below 80%). Synthetic demo data for the 14 indicators; per-session data; dark theme; names approved by Gonzalo; `python -m core.config --strict` has no `TODO` left.

## 4. Live demo script (30 seconds)

**Before the pitch starts** (Advance took 8-10 s on the deployed app before #158; still do it before the pitch so the demo needs no wait): open the app, on the Welcome click **Astronaut A**, then **International Space Station** → Main Menu → Demo controls → **Reset demo**, then **Advance mission 24 h**, and wait until the mascot says an alert needs a repeat measurement. Turn **Voice** on (browsers need one click before audio).

**On stage:** Main Menu (alert waiting) → **Check-in** (chart with the personal baseline) → **Simulate wait** → enter **360** → **Confirm** → Protocols opens → answer **No** to the symptom question → stop at *"Ask the crew medical officer for priority medical review"*.

## 5. Tasks for tonight, by priority

### P0

1. **Finish making "Advance mission 24 h" fast** (detection: Juan Carlos's files; config: Ansel's). The data part is **done** (#158, Fran): CSV parsed once per content, baselines cached, one clock write per batch; locally 3.4 s → 0.7 s with identical results. What is left, from `docs/CODE_REVIEW.md`: **PERF-2** (cache the `config/*.json` loads, invalidated when a file changes, so edits still show up on rerun) and **PERF-3/4** (detection re-validates the same rules for every row; validate once per batch). Same constraints: no change to results, signatures, contracts or `advance_and_detect()` keys; measure before and after with the real seed.
2. **Check-in texts with an active alarm** (Juan Carlos): the mascot still says "Choose a check-in…" while an urgent symptom is active (the Main Menu already says it), and the caption "objective measurements determine alerts" is no longer exact for alarms.
3. **Mascot-first layout** (Ansel's decisions, all taken): big centred mascot with word-by-word subtitles, small on the left with an animation only beside a chart or flowchart, conversational full-viewport Welcome, no mascot on Trends and Tutorials. Full specification: [`FRONTEND_MASCOT_LAYOUT.md`](FRONTEND_MASCOT_LAYOUT.md). Start it after tasks 1 and 2.

### P1

4. **Subjective-symptom details** [Edu content for wording]: v1 only records "I have it now". Edu's `docs/sintomas_subjetivos_atrofia_SANS.md` (section 4) also asks for onset (sudden/gradual), trend, location, **impact** (`task_not_completed` must trigger an immediate safety assessment, triage rule 3), optional intensity 0-10, context and notes. Also his note: new double vision or severe headache with neurological signs needs urgent assessment (not yet an alarm item).
5. **Shorter protocol texts** [Edu content]: the mascot reads every step aloud; one or two sentences per step (`AGENTS.md` 15).
6. **README**: indicators and sources (#111, Edu), remaining AI-usage lines (#113: Edu, Ansel), "Meet the mascot" (Ansel).
7. **Mascot name** (Ansel; `MASCOT_NAME`; the look is decided in task 3). Long term, replace `components.html` (deprecated; Streamlit is pinned to 1.67.0 because of it).
8. **Narrow screens**: the spec asks for usable layouts at narrow widths; not checked yet.

Done since the first version of this file: subjective-symptom list (#146), check-in groups and intervals (#133, #138), protocol structure (#147), Check-in returns to its list without stale messages (#149).

## 6. Before submission (after the Sunday 16:00 freeze, Ansel)

- Translate `docs/sintomas_subjetivos_atrofia_SANS.md` (Edu's source for the symptoms) to English, or replace it with an English summary.
- Delete the internal Spanish documents in `docs/` (`ESTRUCTURA.md`, `Preparación del entorno · NASA Space Apps 2026.md`, `WORKFLOW.md`).
- No `TODO` left in the README; slides link.
- Make the repository public (the app already is).

## 7. Out of scope (documented as future work)

Removing the legacy `triggers` / severity format; a full "not evaluable" model; real (non-synthetic) astronaut data.

## 8. Decisions for the morning

Only decisions that are important for the team to make (see section 1); one line each: task, question, options, recommendation.

- (none yet)

## 9. Night log

**Summary:** Advance mission 24 h is ~2x faster (0.7 → 0.3 s locally, under 2 s live; identical results). Check-in shows active urgent symptoms. Task 3 (mascot-first layout) is done in four PRs: mascot core, Welcome + Menu, Check-in, Tutorials. Live demo path verified on the deployed app after #168.

What the agent merged tonight (one line per PR: number, what, tests) and the minor decisions it took on its own (what and why).

- #163 Task 1 (Advance speed): `core/data.py` caches the clock-filtered sorted table, the (astronaut, indicator) split and `latest_values` per (file content, clock). One advance of the real seed 0.70 s → 0.32 s locally; results byte-identical to `main` (3 environments × 4 advances: episodes, CSV, latest values, baselines, symptom levels). 3 new tests in `tests/test_data_cache.py`.
  - Decided: **PERF-2/3/4 not done**. Profiled after #158: config JSON loads are 43 per advance (~10 ms) and rule validation ~55 ms; the time was pandas filtering (85%). Caching config needs deep copies (as slow as parsing) and validating once needs invalidation logic in Juan Carlos's files: more risk than gain. Reopen only if the deployed timing is still slow.
- #164 Task 2 (Check-in with an active alarm): the Check-in list shows each active alarm with its action and the mascot says the Main Menu's alarm line (alarms prevail, as in the Menu); the subjective-issues caption now says routine issues speed up reminders, alerts come from measurements, urgent symptoms need action at once. 1 new test in `tests/test_check_in_mission_integration.py`.
  - Decided: reused the Main Menu's existing alarm sentence instead of writing a new one (no new health wording).
- #165 Task 3, PR 1/4 (mascot core): `core/mascot.py` rewritten per `FRONTEND_MASCOT_LAYOUT.md` 1 (frameless spec face, 35 %/45 % viewport sizes, word-by-word subtitles synced to the voice, talking mouth, speak only new text, centre ↔ left entry animation, fixed Voice toggle); `AGENTS.md` 3, 8, 16 updated. 9 new tests in `tests/test_mascot.py`. Checked locally in Chrome: reveal, frame fit, move animation.
  - Decided: the Voice toggle sits at `right: 8rem` with `z-index: 1000000`, not `1rem` / `1000`: Streamlit's header (z-index 999990) hid it and its Deploy/menu buttons are at the right edge.
  - Decided: the iframe also resizes its Streamlit element container (`height` and `flex-basis`), otherwise the fallback height left a gap under the subtitles.
  - Decided: `beside()` still draws through `say(size="small")`, so page tests that capture `mascot.say` keep working.
- #166 Task 3, PR 2/4 (Welcome + Main Menu): full-viewport conversational Welcome (astronaut buttons, then environment buttons, "← Change astronaut", no header, no dropdowns/NEXT); Main Menu with the big centred mascot and one row of cards (Protocols first when shown). Demo script (section 4) updated. `tests/test_home_navigation.py` rewritten; Welcome steps of the two Check-in integration tests updated. Checked locally in Chrome at 1568×708: no scroll, Back returns to step 1.
  - Decided: kept the "SpaceDoc" title, caption and "Try it in 1 minute" expander on the Welcome (AGENTS.md 15 asks the Welcome to explain the app); they fit without scrolling.
  - Decided: environment buttons are secondary like the astronaut ones: white text on the cyan primary colour was hard to read.
- #167 Task 3, PR 3/4 (Check-in): list view with the big centred mascot, alarms below it, check-in cards in a 3-column grid; detail view without the Indicator selectbox: one compact chart per indicator of the check-in, stacked (only the repeated one in repeat mode); guidance check over every indicator of the form. Tests in `tests/test_check_in.py` updated, 1 new.
  - Decided: each stacked chart gets its indicator name as a caption (left/right eye charts were indistinguishable), and the detail mascot line is "Record the measurements of this check-in." (the old line asked to choose an indicator, which no longer exists).
- #168 Task 3, PR 4/4 (Tutorials; Protocols unchanged): no mascot or Voice toggle on Tutorials; intro as a paragraph, cards in a 3-column grid; practice step as `st.subheader` over a full-width flowchart; completed step as `st.success`. Protocols already matched section 5 (titles kept: the big mascot fits at 720 px). 1 new test in `tests/test_tutorials_page.py`. Not checked in a browser (usage limit).
- Paused 00:50-01:10 (usage limit), resumed until 06:00 as Ansel asked. Live check after #168 (deployed app): Welcome buttons → Menu → Reset → Advance (alert) → Check-in repeat (Simulate wait, 360, Confirm) → Protocols → No → crew medical officer step: all fine; Tutorials without mascot. For Ansel to check by eye: animation and word-by-word subtitles in Chrome, Edge, Firefox, and the voice.
- Primary buttons readable: dark text on the cyan primary colour, app-wide (`app.py`). Found in the live check: the Main Menu "Protocols" card was white on cyan. (#169)
- #170 Task 6 (README, partial): "Meet the mascot" written (look and behaviour from task 3, name left to the team); "Try it in 1 minute" step 1 without NEXT; broken characters fixed (`?m` → µm, `cm?` → cm², `?` → ×, §, `Fris?n` → Frisén, also in 4 user-visible strings of `config/indicators.json`: spelling only). Slides and Space Apps project links stay `TODO` (only the team has them).
- Task 8 (narrow screens): checked at 390×844 (the app in an iframe; the browser window could not be resized). Everything stacks and works. Fixed: the big face is capped at 55 % of the screen width and subtitles are smaller below 640 px (all three Welcome buttons now fit on a phone); check-in and tutorial cards are laid out in rows of three, so a phone shows them in the configured order (column-major stacking mixed the order).
