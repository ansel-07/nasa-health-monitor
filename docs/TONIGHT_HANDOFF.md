<!-- AI-assisted: generated with Claude Code and reviewed by Ansel. -->

# Tonight's handoff (after v1, Saturday 23:00 → 02:00)

Owner: Ansel. Written at the v1 cut-off for whoever works tonight (people or a coding agent).
**Read `AGENTS.md` first**; this file only lists what is left and how to do it safely.

## 1. Ground rules for tonight

- `v1` is a git tag on the commit that worked in the live rehearsal. If anything breaks, compare with it or go back to it.
- Work in a branch per task (`<name>/short-description`) and in a separate worktree; open a pull request; merge only when `python -m pytest` and `python -m core.config` pass. Never `git push --force` to `main`.
- **Never invent medical content**: thresholds, symptoms, intervals, protocol steps and sources come from Edu (`AGENTS.md` 11). Tasks marked **[Edu content]** below need his input; an agent may only prepare the structure and ask.
- Keep the contracts (`AGENTS.md` 7) and the per-session data rules (5.5). New public functions go into section 7.
- Keep requests short (`AGENTS.md` 14). Gonzalo is not available tonight: his product decisions go to Ansel.
- Feature freeze: **Sunday 16:00**. Integrations: Sunday 13:00.

## 2. State at v1

Works end to end on the deployed app (https://nasa-health-monitor-jyjqxq9oyta7gece258ben.streamlit.app/):
Welcome → Main Menu → Check-in (9 grouped check-ins with bars, multi-field form, confirmation, subjective-issue selector) → Protocols (flowchart, one-click answers, list by severity) · Trends (cards with inline charts) · Tutorials (practice mode, bars, gate below 80%). Synthetic demo data for the 14 indicators; per-session data; dark theme; names approved by Gonzalo.

## 3. Live demo script (30 seconds)

**Before the pitch starts** (Advance takes 8-10 s on the deployed app, see task 1): open the app, choose Astronaut A + International Space Station → NEXT → Main Menu → Demo controls → **Reset demo**, then **Advance mission 24 h**, and wait until the mascot says an alert needs a repeat measurement. Turn **Voice** on (browsers need one click before audio).

**On stage:** Main Menu (alert waiting) → **Check-in** (chart with the personal baseline) → **Simulate wait** → enter **360** → **Confirm** → Protocols opens → **Continue** → answer **No** → stop at *"Ask the crew medical officer for priority medical review"*.

## 4. Tasks for tonight, by priority

### P0

1. **Make "Advance mission 24 h" fast** (Juan Carlos: detection; Fran: data). It processes 42 rows one by one and each call re-reads the CSV, baselines and config; 8-10 s on the deployed app. Goal: under 2 s, same results. Ideas: read config, latest values and baselines once per batch and pass them down; avoid rewriting `measurements.csv` per row. Detection semantics, tests and contracts must not change (`advance_and_detect()` keeps its signature and return keys).
2. **Subjective issues list** [Edu content] (#98): `config/subjective_issues.json` has no real issues, so the Check-in selector is empty. Edu writes the issues and their check-in links with sources.
3. **Check-in polish** (Juan Carlos): after a confirmed alert, going back to Check-in later still shows "Repeat measurement recorded…" and opens the last check-in instead of the list. Show the list and drop the stale message.

### P1

4. **Protocol structure** [Edu content] (#137, Javi → Edu): loop, flight-surgeon contacts, redundant steps.
5. **Review intervals** [Edu content] (#98): `tutorial_bar_full_days` per protocol (now `TODO_EDU`) and `bar_full_hours` per check-in (24 h placeholders; Gonzalo did not approve one value for all).
6. **Shorter protocol texts** [Edu content]: the mascot reads every step aloud; one or two sentences per step (`AGENTS.md` 15).
7. **README**: "The problem" (#112, now Ansel), indicators and sources (#111, Edu), remaining AI-usage lines (#113: Gonzalo, Edu, Ansel), "Meet the mascot" (Ansel).
8. **Mascot look and name** (Ansel; `core/mascot.py`, `MASCOT_NAME`). Long term, replace `components.html` (deprecated; Streamlit is pinned to 1.67.0 because of it).

### Open pull requests at the cut-off

- #138 (Edu): non-subjective configuration for #98 — review next.

## 5. Before submission (after the Sunday 16:00 freeze, Ansel)

- Delete the internal Spanish documents in `docs/` (`ESTRUCTURA.md`, `Preparación del entorno · NASA Space Apps 2026.md`, `WORKFLOW.md`).
- No `TODO` left in the README; slides link.
- Make the repository public (the app already is).

## 6. Out of scope (documented as future work)

Removing the legacy `triggers` / severity format; a full "not evaluable" model; real (non-synthetic) astronaut data.
