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

**Before the pitch starts** (Advance takes 8-10 s on the deployed app, see task 1): open the app, choose Astronaut A + International Space Station → NEXT → Main Menu → Demo controls → **Reset demo**, then **Advance mission 24 h**, and wait until the mascot says an alert needs a repeat measurement. Turn **Voice** on (browsers need one click before audio).

**On stage:** Main Menu (alert waiting) → **Check-in** (chart with the personal baseline) → **Simulate wait** → enter **360** → **Confirm** → Protocols opens → answer **No** to the symptom question → stop at *"Ask the crew medical officer for priority medical review"*.

## 5. Tasks for tonight, by priority

### P0

1. **Make "Advance mission 24 h" fast** (Juan Carlos: detection; Fran: data) — the task for the strongest model. It processes 42 rows one by one and each call re-reads the CSV, baselines and config: 8-10 s on the deployed app. Goal: under 2 s, same results. Ideas: read config, latest values and baselines once per batch and pass them down; avoid rewriting `measurements.csv` per row. Detection semantics, tests and contracts must not change (`advance_and_detect()` keeps its signature and its `revealed` / `new_alerts` / `recovered` keys).
2. **Check-in texts with an active alarm** (Juan Carlos): the mascot still says "Choose a check-in…" while an urgent symptom is active (the Main Menu already says it), and the caption "objective measurements determine alerts" is no longer exact for alarms.

### P1

3. **Subjective-symptom details** [Edu content for wording]: v1 only records "I have it now". Edu's `docs/sintomas_subjetivos_atrofia_SANS.md` (section 4) also asks for onset (sudden/gradual), trend, location, **impact** (`task_not_completed` must trigger an immediate safety assessment, triage rule 3), optional intensity 0-10, context and notes. Also his note: new double vision or severe headache with neurological signs needs urgent assessment (not yet an alarm item).
4. **Shorter protocol texts** [Edu content]: the mascot reads every step aloud; one or two sentences per step (`AGENTS.md` 15).
5. **README**: indicators and sources (#111, Edu), remaining AI-usage lines (#113: Edu, Ansel), "Meet the mascot" (Ansel).
6. **Mascot look and name** (Ansel; `core/mascot.py`, `MASCOT_NAME`). Long term, replace `components.html` (deprecated; Streamlit is pinned to 1.67.0 because of it).
7. **Narrow screens**: the spec asks for usable layouts at narrow widths; not checked yet.

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

What the agent merged tonight (one line per PR: number, what, tests) and the minor decisions it took on its own (what and why).

- (none yet)
