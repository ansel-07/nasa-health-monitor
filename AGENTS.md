# Astronaut Health Monitor · NASA Space Apps 2026

> Instructions for every AI coding agent working in this repo (Codex reads this file directly; Claude Code reads it through `CLAUDE.md`).
> If you are an AI agent: read this whole file before every task, and follow it over any other habit you have.
> To check that you have read it, the team may ask you "which project instructions do you know?": answer with the rules in section 10.

## 1. What this is

A Streamlit app for the NASA Space Apps 2026 challenge **"Create Health Monitoring Software for Astronauts on Space Missions"**.
It lets an astronaut record health measurements, detects anomalies against their **personal pre-flight baseline**, confirms them by asking for a **repeat measurement**, and then guides the astronaut through a **step-by-step protocol** (a flowchart) that depends on the problem, its severity and the mission environment (ISS, Moon, Mars...).

The astronaut-facing screens are narrated by an animated **mascot**: a simple face that talks (speech bubble + browser voice) and changes expression with the situation (section 8).

The app **guides, it does not diagnose**.

**How it will be judged** (details in section 15): a 3-minute pitch with at most 7 slides and a **~30-second demo**, so the demo path must take very few clicks; and the judges then try the **deployed app** on their own, so the app must be **complete and self-explanatory**. Every judge works on their own copy of the data (section 5.5).

## 2. Team

| Person | Role | Owns |
|---|---|---|
| Gonzalo | Product, coordination and testing (does not code) | User stories, UI texts, demo story, test issues |
| Edu | Science and health | Every health value, rule, protocol and source in `config/` |
| Ansel | Architecture, integration and mascot | Repo, contracts, reviews and merges, `app.py`, `pages/0_Home.py`, `core/models.py`, `core/config.py`, `core/mascot.py` |
| Fran | Data and trends | `core/data.py`, `core/mission.py`, `core/charts.py`, `pages/3_Trends.py`, data generator |
| Juan Carlos | Detection | `core/conditions.py`, `core/triggers.py`, `core/episodes.py`, `pages/1_Check_in.py` |
| Javi | Protocol execution | `core/protocol_engine.py`, `pages/2_Protocol.py` |

## 3. Stack

- Python 3.12, Streamlit **1.67.0 (pinned in `requirements.txt`: the tested version; the mascot uses `st.iframe`, no longer the deprecated `components.html`; do not upgrade without Ansel)**, pandas, Plotly, numpy. pytest for tests (always run as `python -m pytest`).
- Always work inside the project virtual environment (`.venv`). Use Python 3.12: newer versions (3.14) may fail to install some packages.
- **Do not add any other library without asking Ansel.**
- Storage: CSV and JSON files. No database server. In the app, each browser session has its own copy of `data/seed/` (section 5.5).
- Multipage Streamlit app: `app.py` is the entry point and only sets the navigation (`st.navigation`); every screen is a file in `pages/`. **A new page must be added to the list in `app.py`**, or it will not appear.
- **Screens and navigation** follow `docs/ASTRONAUT_HEALTH_APP_SPEC.md` (Gonzalo) with the overrides of section 16. No sidebar menu: people move with buttons and cards. Welcome (conversational buttons: astronaut, then environment; no dropdowns, no NEXT) → Main Menu → Check-in (list → detail) · Trends · Tutorials; Protocols opens only from a confirmed alert (or an active episode). Use `st.switch_page("pages/<file>.py")` for every button that changes screen. Theme: `.streamlit/config.toml` (colours of the spec).
- Mascot: SVG/CSS/JS inside `st.iframe` (HTML string, same-origin). No image files, no external services.
- **Look:** `docs/UI_STYLE.md` (Ansel): no page titles, mission status bar, theme and IBM Plex fonts in `.streamlit/config.toml` + `static/fonts/`, shared styles in `core/ui.py`, Material icons, no emojis.

## 4. Repository layout and owners

Each file has **one owner**. Only change files you were asked to change. If you need something from a file you do not own, use the contract in section 7 and, if it is not implemented yet, call the stub that is already there.

```
app.py                      Ansel        Entry point: page config and navigation (sidebar names); things shown on every screen
pages/0_Home.py             Ansel        Welcome: pick astronaut and mission (no default), NEXT
pages/5_Menu.py             Ansel        Main Menu: Check-in, Trends, Tutorials cards; demo controls
pages/1_Check_in.py         Juan Carlos  Measurement form, trigger alert, confirmation step (with mascot)
pages/2_Protocol.py         Javi         Protocols: active/pending ones by severity, step by step (with mascot)
pages/4_Tutorials.py        Javi         One practice tutorial per protocol, with its bar (with mascot)
pages/3_Trends.py           Fran         History charts with colour bands and personal baseline (no mascot)
core/models.py              Ansel        Shared constants: severities, statuses, node types, moods, paths
core/config.py              Ansel        Load and validate config/*.json
core/mascot.py              Ansel        The mascot: face, expressions, speech bubble, voice
core/ui.py                  Ansel        Shared look: global styles, mission status bar (docs/UI_STYLE.md)
core/data.py                Fran         Measurements, baseline, astronauts, episodes (read/write)
core/mission.py             Fran         Simulated mission clock
core/activity.py            Fran         Activity bars (check-ins, tutorials) and subjective-issue history
core/charts.py              Fran         Reusable Plotly charts (used by Trends AND by Check-in)
core/conditions.py          Juan Carlos  Shared condition evaluator (section 5)
core/triggers.py            Juan Carlos  Evaluate a new measurement against the problems
core/episodes.py            Juan Carlos  Open, confirm, dismiss, pending list, one-at-a-time rule
core/protocol_engine.py     Javi         Current step and advance with the astronaut's input
config/*.json               Edu          Health content (format owned by Ansel)
config/protocols/*.json     Edu          Protocol flowcharts (format owned by Ansel)
.streamlit/config.toml      Ansel        Theme (colours of the spec)
data/                       Fran         data/seed/ = demo starting point, copied into every new browser session (5.5); data/*.csv|json = used by scripts only
scripts/generate_data.py    Fran         Generates pre-flight and simulated mission data
tests/                      Ansel        Each builder adds tests for their own part
```

## 5. Data formats

### 5.1 Measurements · `data/measurements.csv`

One row per measurement:

```
timestamp,astronaut,indicator,value,unit,phase,source
2027-04-10T08:00:00,a1,peripapillary_trt_left,312.4,µm,mission,manual
```

- `timestamp`: ISO 8601, mission time (see `core/mission.py`), no timezone.
- `indicator`: a key of `config/indicators.json`. Blood pressure is **two indicators**: `bp_systolic` and `bp_diastolic`.
- `phase`: `preflight` | `mission`.
- `source`: `simulated` | `manual` | `protocol`.

### 5.2 Baseline

For each astronaut and indicator: mean and standard deviation of the `preflight` measurements. Returned as `{"mean": float, "std": float, "n": int}`. z-score = (value − mean) / std.

- It is the **only** reference for baseline-relative conditions (section 6). It is frozen by construction: pre-flight rows do not change during the mission.
- A baseline is **valid** only with `n >= 2` and `std > 0` (and `mean > 0` for `baseline_fraction`).
- **Never pool sites:** one indicator id per eye and per muscle/site/method (e.g. `refraction_left`, `refraction_right`), so every baseline compares like with like.
- **Not evaluable** (no valid baseline, or a value missing): the condition is not satisfied, **but the result is never shown as normal**: Check-in keeps the measurement and says the indicator cannot be evaluated yet (no valid pre-flight baseline), and a confirmation never dismisses an episode because of it. No new API or episode status. A full "not evaluable" model (three-valued API, reference metadata, re-evaluation) is out of scope for the hackathon (README, future work).

### 5.3 Config files (in `config/`)

- `mission.json`: mission name, start time, default environment, astronauts.
- `indicators.json`: `{indicator_id: {name, unit, how_to_measure, why_it_matters, source}}`.
- `environments.json`: `{env_id: {name, gravity_g, comm_delay_min, source}}`. `comm_delay_min` is one-way.
- `problems.json`: `{problem_id: {name, description, hrp_risk, confirm_wait_min, protocol, symptoms, states, source}}`. A problem is a set of **symptoms**; each symptom has a **level**, and the levels decide the **state** of the problem:
  - `symptoms`: `{symptom_id: {name, levels}}`. `levels` is a list of `{level, when, environments?}` with `level` in `SYMPTOM_LEVELS` (`watch`, `concern`). `when` is a condition on **indicators only** (section 6), evaluated with the **latest value** of each indicator. If `environments` is present, the rule only applies there. **The first matching rule wins**, so write them from most to least serious; no match = `not_present`.
  - `states`: list of `{state, when}` with `state` in `PROBLEM_STATES` (`watch`, `medical_urgency`). `when` is a condition on **symptoms** (`symptom` + `level_at_least` / `level_is`, `count_at_least` + `of`), optionally with `environment_in`. **The first matching rule wins**; no match = `no_concern`. Only the symptom level matters (no weights or scores).
  - The problem state is the episode **severity**: an episode opens when the state is `watch` or worse.
  - **Attribution (#91):** a new measurement raises a symptom-based alert only if the symptom it feeds (its own `levels`) is `watch` or `concern`; the episode `trigger` is that measurement, so confirmation repeats it. A normal measurement never raises an alert caused by another indicator, even if the problem state is still `watch`.
  - **TRANSITION** (until every owner has migrated): the old `triggers` list (`{severity, when, environments?}`, highest severity wins) and the old `SEVERITIES` names still work. New content uses `symptoms` + `states` only. `_example` has both formats.
- `protocols/<problem_id>.json`: `{problem, start, nodes}` (section 9).

Problem ids starting with `_` (like `_example`) are **test fixtures**, never shown as real health content.
Values still to be written by a person start with `TODO` (`TODO_EDU`, `TODO_GONZALO`): `python -m core.config --strict` lists them.

### 5.4 Episodes · `data/episodes.json`

```json
{
  "episodes": [
    {
      "id": "ep-0001", "astronaut": "a1", "problem": "sans", "environment": "mars",
      "status": "active", "severity_initial": "watch", "severity": "watch",
      "trigger": {"indicator": "peripapillary_trt_left", "value": 360, "z": 12.0, "measured_at": "2027-04-10T08:00:00"},
      "current_node": "remeasure", "vars": {"trt_after": 358}, "answers": {},
      "log": [{"at": "2027-04-10T08:12:00", "node": "do_action", "input": "done"}],
      "opened_at": "2027-04-10T08:05:00", "closed_at": null, "outcome": null
    }
  ],
  "pending": [
    {"astronaut": "a1", "problem": "muscle_atrophy", "severity": "watch", "indicator": "muscle_strength",
     "value": 390, "z": -4.4, "measured_at": "2027-04-10T08:00:00"}
  ]
}
```

Episode `status`: `pending_confirmation` → `active` or `dismissed`; `active` → `resolved` | `monitoring` | `handed_over` (set by an `end` node, also stored in `outcome`).
Symptom-based problems also store `"symptoms": {symptom_id: level}` on the episode: the levels at the last detection (opening or confirmation).

### 5.5 Per-session data (deployed app)

The app is deployed on Streamlit, so all judges use **one server**. To keep them from seeing or resetting each other's data:

- Inside the app, every **browser session** works on its own folder in the system temp directory, created as a copy of `data/seed/` the first time it is used. Reset demo copies `data/seed/` again **into that session only**. A browser refresh or a new tab starts a fresh session. Folders older than 24 hours are deleted.
- Outside the app (scripts, tests) there is no session: files are read and written in `data/` as before.
- `mission_state.json` is `{"now": ISO time}` plus, after a failed detection, `"unprocessed": [measurement dicts]`: rows revealed by an advance that detection did not finish; the next `advance_and_detect()` processes them first (#77). Reset demo clears it.
- **Only `core/data.py` and `core/mission.py` touch data files**, and always through `models.data_file(models.<X>_FILE)` / `models.data_dir()`; never use `models.<X>_FILE` directly to read or write.
- So `data/seed/` **is the demo**: what a new session sees first. To change the demo starting point, regenerate `data/seed/` (`scripts/generate_data.py`); the app never writes to it.
- Tests: `tests/conftest.py` turns session data off (`models.SESSION_DATA = False`), so tests keep patching `models.<X>_FILE`. `tests/test_session_data.py` covers the per-session behaviour.

### 5.6 Check-ins, activity bars and subjective issues

From `docs/ASTRONAUT_HEALTH_APP_SPEC.md` (sections 3-4), adapted to this repo:

- `config/checkins.json`: `{checkin_id: {name, indicators: [...], bar_full_hours}}`. A **check-in** is a group of indicators measured in the same test (one card in the Check-in list, one form). Every indicator used by a real problem is in **exactly one** check-in. Each submitted value still goes through detection and confirmation **per indicator** (section 10).
- **Activity bars** (`core/activity.py`): `BAR_LEVELS` 100..0 in 10-point steps, from the last completion and the **mission clock** (`mission.now()`), so advancing mission time drains them. Never completed = 0. A check-in bar refills to 100 when its check-in session ends; a tutorial bar when the tutorial is completed. **A bar is not a health status and never blocks a measurement or an active protocol.**
- Durations: check-in bar 100 → 0 in `bar_full_hours` (spec demo default 24); tutorial bar 100 → 0 in `tutorial_bar_full_days` of each problem (`problems.json`, Edu: more important protocols are reviewed more often). A tutorial can be repeated only when its bar is **below 80** (`TUTORIAL_REPEAT_BELOW`).
- `config/subjective_issues.json`: `{"settings": {persistence_days, speed_multiplier}, "issues": {issue_id: {label, check_ins: [...]}}}`. Issues and their check-in links come from Edu; settings are demo placeholders from the spec. An issue reported on `persistence_days` calendar days makes its linked check-in bars drain `speed_multiplier` times faster from then on (not retroactively); resolving it stops the acceleration (no refill). A subjective issue never opens an episode by itself. Issues come from Edu's `docs/sintomas_subjetivos_atrofia_SANS.md`: 12 routine symptoms (`MUS_*`, `VIS_*`, each with its `question` and check-in links decided by Ansel) and 4 **alarms** (`ALM_*`: `"alarm": true`, an `action`, no check-in links). Reporting an alarm shows its action at once, and the Main Menu keeps it visible until the astronaut marks it resolved; it never closes by itself and does not open a SANS or muscle-atrophy episode.
- **Details of a report** (optional, Edu's section 4): onset, trend, location (eye for `VIS_*` issues, else free text), impact, intensity 0-10 (the astronaut's own rating, never a threshold), context, notes; ids in `activity.ISSUE_DETAIL_CHOICES` / `EYE_LOCATIONS`. Stored on that day's report; a later save the same day replaces them. `impact = task_not_completed` shows that an immediate safety assessment is needed (triage rule 3); details never open an episode.
- Storage: `data/activity.json` (completions and issue history, per astronaut) through `models.data_file()`.

## 6. Condition language (`core/conditions.py`)

One evaluator for **both** triggers and protocol decisions. A condition is a JSON object:

| Keys | True when |
|---|---|
| `indicator` + `above` / `below` | latest value of that indicator is above / below the number (strict: > / <) |
| `indicator` + `at_least` / `at_most` | latest value of that indicator is ≥ / ≤ the number |
| `indicator` + `z_above` / `z_below` | its z-score against the astronaut's baseline is above / below |
| `var` + `above` / `below` / `at_least` / `at_most` / `z_above` / `z_below` | same, for a value stored by a `measure` node (`save_as`) |
| `indicator` or `var` + `metric` + `above` / `below` / `at_least` / `at_most` | compares a value derived from x and the baseline mu / sigma (5.2): `raw` (default) x · `baseline_fraction` x / mu · `baseline_delta` x − mu (signed, in the indicator's unit) · `z_score` (x − mu) / sigma · `abs_z_score` abs(z). Several bounds are ANDed, e.g. `{"indicator": "trt_left", "metric": "baseline_delta", "at_least": 20, "below": 55}`. Do not mix `metric` with `z_above` / `z_below` (those stay as the legacy form of strict `z_score`). Without a valid baseline it is not satisfied (not evaluable, 5.2). Names in `CONDITION_METRICS` (`core/models.py`). |
| `severity_at_least` / `severity_is` | current episode severity (order in `core/models.py`) |
| `environment_in` | current environment is in the list |
| `answer` + `equals` | the answer stored by a `question` node equals the value |
| `all` / `any` | list of conditions, combined with AND / OR |
| `count_at_least` + `of` | at least N of the conditions in the `of` list are true |
| `symptom` + `level_at_least` / `level_is` | current level of that symptom of the problem (order in `SYMPTOM_LEVELS`) |

`ctx` passed to `check(cond, ctx)`:
`{"astronaut", "environment", "severity", "vars", "answers", "latest": {indicator: value}, "symptoms": {symptom_id: level}, "var_indicators": {save_as: indicator}}`.
`var_indicators` is built by the protocol engine from its `measure` nodes; it is required for `var` conditions that use the baseline (`z_above` / `z_below` or a `metric` other than `raw`).
`symptoms` comes from `triggers.symptom_levels()`; symptom conditions are allowed in `states` and in protocol `decision` nodes, never inside a symptom's own `levels`.

## 7. Function contracts

Do not change a signature without asking Ansel. Until a function is implemented it is a **stub** that returns fake data in the right format (marked `# STUB`).

```python
# core/models.py  (Ansel)
SEVERITIES, SYMPTOM_LEVELS, PROBLEM_STATES, CONDITION_METRICS, EPISODE_STATUSES, OPEN_STATUSES, OUTCOMES, NODE_TYPES, PHASES, SOURCES, MOODS
data_dir() -> Path                 # runtime data folder of the current session (DATA_DIR outside the app)
data_file(default: Path) -> Path   # e.g. data_file(MEASUREMENTS_FILE): that file in the current session (5.5)
severity_rank(severity) -> int
max_severity(a, b) -> str

# core/config.py  (Ansel)
load_mission() -> dict
load_indicators() -> dict
load_environments() -> dict
load_problems(include_examples: bool = False) -> dict
load_protocol(problem_id: str) -> dict
load_checkins(include_examples: bool = False) -> dict
load_subjective_issues(include_examples: bool = False) -> dict
validate_all(strict: bool = False) -> list[str]   # error messages; empty if OK

# core/mascot.py  (Ansel)
say(text: str, mood: str = "neutral", size: str = "large") -> None
beside(text: str, mood: str = "neutral") -> DeltaGenerator   # mascot small on the left; returns the right column for the visual
# Draws the mascot with subtitles and reads `text` aloud. mood: one of MOODS. size: "large" (Welcome only) | "medium" (alone on other screens) | "small" (beside()).
voice_toggle() -> None   # "Voice on/off" control; draw it once per astronaut screen

# core/data.py  (Fran)
load_astronauts() -> pd.DataFrame                  # columns: id, name, role
load_measurements(astronaut=None, indicator=None, phase=None) -> pd.DataFrame
add_measurement(m: dict) -> None                   # keys = columns of 5.1
get_baseline(astronaut: str, indicator: str) -> dict | None
z_score(astronaut: str, indicator: str, value: float) -> float | None
latest_values(astronaut: str) -> dict              # {indicator: last value}
load_episodes(astronaut: str | None = None) -> list[dict]
save_episode(episode: dict) -> None                # create or replace by id
get_open_episode(astronaut: str) -> dict | None    # pending_confirmation or active
load_pending(astronaut: str | None = None) -> list[dict]
save_pending(items: list[dict]) -> None            # replaces the whole pending list
reset_demo() -> None                               # copy data/seed/* over this session's data (5.5)

# core/mission.py  (Fran)
now() -> datetime
advance(hours: int = 24) -> list[dict]             # new simulated measurements now visible
advance_and_detect(hours: int, environment: str) -> dict   # advance + detection for every astronaut (#58)
# returns {"revealed", "new_alerts", "recovered"}: recovered = leftover rows of a failed run processed now (#77, P1)

# core/activity.py  (Fran)  -- 5.6
bar_level(astronaut: str, kind: str, activity_id: str) -> int   # kind: "check_in" | "tutorial"; a BAR_LEVELS value
complete(astronaut: str, kind: str, activity_id: str) -> None   # bar back to 100 (mission time)
can_repeat_tutorial(astronaut: str, protocol_id: str) -> bool   # bar < TUTORIAL_REPEAT_BELOW
report_issues(astronaut: str, issue_ids: list[str], source: str) -> None   # source: "check_in_list" | "check_in_detail"
resolve_issue(astronaut: str, issue_id: str) -> None
active_issues(astronaut: str) -> list[dict]   # [{"issue", "since", "persistent", "details"}]
add_issue_details(astronaut: str, issue_id: str, details: dict) -> None   # optional details of today's report (5.6)
needs_safety_assessment(details: dict | None) -> bool   # impact == "task_not_completed" (Edu's triage rule 3)

# core/charts.py  (Fran)
indicator_chart(astronaut: str, indicator: str, compact: bool = False,
                environment: str | None = None) -> plotly.graph_objects.Figure
# One indicator over time: personal baseline, colour bands, episode marks.
# compact=True is the small version shown inside Check-in. Pages draw it with st.plotly_chart(fig).
# environment: the current environment; adds the bands of rules that only apply there (None: only general bands).

# core/conditions.py  (Juan Carlos)
check(cond: dict, ctx: dict) -> bool

# core/triggers.py  (Juan Carlos)
evaluate(measurement: dict, environment: str) -> list[dict]
# one item per matching problem: {"problem", "severity", "indicator", "value", "z", "symptoms"?}
# For symptom-based problems: "severity" is the problem state, "symptoms" is {symptom_id: level}.
symptom_levels(problem_id: str, astronaut: str, environment: str) -> dict   # {symptom_id: level}, latest values only
assessment_issues(problems: dict, astronaut: str, indicator: str, environment: str) -> list[str]
# Check-in warnings (5.2 "not evaluable"): at most two messages; never changes data or episodes

# core/episodes.py  (Juan Carlos)
on_new_measurement(measurement: dict, environment: str) -> dict | None
# Single entry point, called by Check-in and after mission.advance().
# Applies confirmation and the one-open-episode-per-astronaut rule; returns the open episode, if any.
confirm(episode_id: str, measurement: dict) -> dict   # -> active (severity from this measurement) or dismissed
get_pending(astronaut: str) -> list[dict]
accept_pending(astronaut: str, environment: str) -> dict | None   # start confirmation of the most severe pending alert

# core/protocol_engine.py  (Javi)
current_step(episode: dict) -> dict      # the node, with id and display-ready text
submit(episode: dict, user_input: dict | None) -> dict
flowchart_dot(episode: dict, whole: bool = False) -> str   # Graphviz DOT of the protocol, current step highlighted
# Advances one or more nodes (decision and set_severity nodes run without input),
# stores measurements (source="protocol"), updates severity, closes on `end`, saves the episode.
```

Streamlit session state (created by the Welcome, `pages/0_Home.py`): `st.session_state["astronaut"]`, `st.session_state["environment"]`, `st.session_state["voice_on"]`.

## 8. The mascot

Layout decided by Ansel; details in `docs/FRONTEND_MASCOT_LAYOUT.md` (it wins over the spec here):

- **Where it appears:** Welcome, Main Menu, Check-in and Protocols. **Not** on Trends or Tutorials.
- **Look:** the spec face (cyan eyes and smile, no frame) with **subtitles below it** (no speech bubble).
- **Alone on the screen:** on the Welcome `mascot.say(text, mood, size="large")`, big (35 % of the browser height) and centred; on every other screen `size="medium"`, a compact assistant line (face at most 112 px left of its subtitles, in a panel; Ansel, `docs/UI_STYLE.md`). Cards and buttons are **not** a visual: they go below the subtitles (Welcome, Main Menu, Check-in list, every Protocols state without a step).
- **Only with a chart or a flowchart** (Check-in detail, an active protocol step): `mascot.beside()`; the mascot slides to the left and shrinks (a 600 ms entry animation, once), the visual takes the right. **Buttons always go below**, full width.

  ```python
  with mascot.beside(text, mood):
      st.plotly_chart(charts.indicator_chart(astronaut, indicator, compact=True, environment=environment))
  if st.button("Record measurement"):
      ...
  ```
- **Subtitles** appear word by word (with the voice when it is on) while the mouth talks. The mascot **speaks only a new text**: a rerun with the same text shows the full subtitles silently.
- **What it says:** the text the screen would otherwise show (alerts, confirmation requests, protocol steps). Pages pass the text; the mascot never invents health content. Keep it short: it is read aloud (section 15).
- **Mood:** one of `MOODS` in `core/models.py`. Which mood goes with which situation is still to be decided by the team.
- **Voice:** the browser's own speech synthesis, in English, no AI service. Muted until the astronaut turns it on with the **Voice toggle, fixed in the top-right corner** (browsers block audio before a user action); turning it on speaks the current line at once.
- **Name:** still to be decided by the team. Design it ourselves; do not copy existing characters, code or artwork.
- Pages call only `mascot.say()`, `mascot.beside()` and `mascot.voice_toggle()`, at most one mascot per screen run; never write mascot HTML in a page.

## 9. Protocol flowcharts (`config/protocols/<problem_id>.json`)

```json
{"problem": "sans", "start": "first_node", "nodes": {"first_node": {"type": "...", "...": "..."}}}
```

| `type` | Shown to the astronaut | Fields |
|---|---|---|
| `info` | An explanation | `text`, `next` |
| `action` | Something to do in real life (e.g. drink water); buttons "Done" / "I can't" | `text`, `next`, `wait_min?`, `next_if_cannot?`, `source?` |
| `measure` | Asks for a measurement; saved to measurements.csv and to `vars[save_as]` | `indicator`, `save_as`, `next`, `text?` |
| `question` | A closed question (symptoms, yes/no) | `text`, `save_as`, `options: {value: next_node}` |
| `decision` | Nothing; branches automatically | `branches: [{"if": condition, "next": node}]`, `default` |
| `set_severity` | Nothing (or a short notice); changes the episode severity | `severity`, `next` |
| `contact` | Notifies the crew medical officer or flight surgeons; shows when an answer could arrive (2 × `comm_delay_min`) | `target: crew_medical_officer \| flight_surgeon`, `text`, `next` |
| `end` | Closes the episode | `outcome: resolved \| monitoring \| handed_over`, `text` |

Severity and environment do **not** create separate files: they are branches (`decision` nodes) inside one protocol per problem.
For symptom-based problems, `decision` nodes can also branch on symptom levels (section 6), and `set_severity` / `severity_at_least` use the `PROBLEM_STATES` names.
`config/protocols/_example.json` uses every node type and is the fixture for building and testing the engine.

## 10. Behaviour rules

1. Triggers are evaluated only on **new** measurements (manual, protocol or revealed by `mission.advance()`). Simulated history never opens episodes.
2. When a trigger fires and the astronaut has no open episode: create an episode with status `pending_confirmation` and ask to **repeat the same indicator** after `confirm_wait_min` (the demo has a "Simulate wait" button). If the repeat also triggers, the episode becomes `active` with the severity given by the repeat; otherwise `dismissed`.
3. **One open episode per astronaut.** Other triggers go to `pending`. When the episode closes, offer the most severe pending one; it goes through confirmation again.
4. Severity starts with the trigger and can change only through `set_severity` nodes.
5. Measurements taken inside a protocol do not open new episodes for the same problem.

## 11. Rules for AI agents

- **English everywhere**: UI text, mascot lines and voice, code, comments, commit messages, docs the jury can see.
- **Never invent medical values.** Every threshold, range, wait time or health advice comes from `config/` files written by Edu. If a value you need is missing or starts with `TODO`, stop and say so; do not fill it in.
- **Touch only the files you were asked to.** Never edit another owner's file, not even "a small fix": open a request for the owner (section 14).
- **Small changes.** One feature or fix per request. Do not rewrite whole files. Do not reorganise the project.
- **Keep the contracts** in section 7. Do not rename functions, parameters, JSON keys or CSV columns.
- Runtime data is read and written **only by `core/data.py` and `core/mission.py`, through `models.data_file()`** (section 5.5).
- Pages (`app.py` and `pages/`) **never read or write files directly**: they only call `core/`. Charts come from `core/charts.py`, the mascot from `core/mascot.py`.
- No new libraries, no new top-level folders, no secrets or API keys in the code.
- Add a test in `tests/` when you add logic in `core/`. Keep `python -m pytest` green.
- **Mark AI-generated code.** Every new file starts with a header comment: `# AI-assisted: generated with <tool> and reviewed by <person>.` (NASA Space Apps requires AI-generated code to be acknowledged in text and metadata).
- At the end of every task, say **which files you changed and how to test it** in one or two lines.

## 12. Commands

```bash
python3.12 -m venv .venv && source .venv/bin/activate  # Windows: py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
python -m pytest
python -m core.config             # validates config/ and prints errors
python -m core.config --strict    # also lists values still marked TODO
```

## 13. Git workflow

- **Deploy** (Streamlit Community Cloud): main file `app.py`, **Python 3.12** in Advanced settings, branch `main`.

- `main` always starts. Run the app and `python -m pytest` before every push.
- One branch per task: `<name>/short-description` (e.g. `juancarlos/confirmation-step`). Open a pull request; Ansel reviews and merges.
- **Exception, Saturday night after v1 (until Ansel says otherwise):** one coding agent works alone and merges its own pull requests under the rules and self-review checklist of `docs/TONIGHT_HANDOFF.md`.
- Small commits with messages that say what changes. Commit every time something works.
- If the pull request completes a request (section 14), write `Closes #<issue>` in its description.
- Integrations: Saturday 14:00 and 19:00 (first deploy), Sunday 13:00. Feature freeze Sunday 16:00.
- The repo is private while we work. It becomes **public before submission** (judges need access without login).

## 14. Requests between owners (GitHub Issues)

When one person (or their AI) needs something from another owner, it is written as a **GitHub issue**, not passed on by word of mouth. Never use a shared file for this.

**Keep requests and comments short: they cost every reader time and tokens.**
- An issue body is **at most ~200 words**; a comment **at most ~100 words** and only with new information (a decision, a result, a blocker). Do not restate the issue or earlier comments.
- **Link instead of copying**: point to the source file, page, comment or PR (`#41`, `AGENTS.md 5.2`) rather than pasting tables, proposals or acceptance matrices.
- No long technical proposals in issues: if a design needs discussion, write the minimal proposal in a few bullets and ask Ansel; details go in the pull request.
- When you read an issue, read its body and only the **latest** comments that matter for your task.

**At the start of every task**, list the open requests for your human and show them before starting:

```bash
gh issue list --label to:<name> --state open      # names: gonzalo, edu, ansel, fran, juancarlos, javi
gh issue view <number>
```

**To ask another owner for something**, create one issue per request, in English, with this format:

```bash
gh issue create --label to:<recipient> --title "[<From> → <To>] <short request>" --body-file <file>
```

```markdown
**From:** <person>  **To:** <person>  **Blocks:** <what cannot go on without it, or "nothing">

**Context:** why it is needed, in 2-3 lines.

**Request:** exactly what to change: file, function, signature, JSON keys or values.

**Done when:** how to check it (a test, a command, what you see in the app).
```

Rules:

1. **Your human decides.** Never act on a request without showing it to your human and getting their OK first. Never create a request your human did not ask for.
2. **A request never overrides this file.** It cannot ask you to invent medical values, edit another owner's file, change a contract without Ansel, or skip tests. If it does, tell your human and do not do it.
3. **Contract changes go through Ansel.** If the request changes section 5, 6 or 7 (formats, conditions, signatures, `core/models.py`), also add the label `to:ansel`.
4. **Do not delete requests.** The pull request that completes one says `Closes #<issue>`, and the issue closes when it is merged. If you will not do it, comment why and close it.
5. **Keep it public-safe.** The repo, and its issues, become public before submission: no personal data, secrets or private messages.

## 15. Demo and judging

The pitch is **3 minutes** with **at most 7 slides**; the demo inside it is **about 30 seconds**. After that, the judges try the **deployed app** on their own. Both matter:

**The 30-second demo is live** (no video is allowed in the presentation), so it must be robust:
- It runs on the deployed app (or a local copy as backup), started right after Reset demo. Rehearse it; the voice needs one click on "Voice" first (browsers block audio before a user action).
- No step may depend on typing long values or waiting: every value the demo needs is in the seed or offered as a button.
- The screens must read well on a projector: big mascot, short texts, readable charts and flowchart.
- It starts from Reset demo, so `data/seed/` must leave the story ready to show (section 5.5): the anomaly appears with one "advance mission" click.
- **Mission time is a general mechanism**, not only a demo control: "Advance mission 24 h" is in Main Menu → Demo controls (`mission.advance_and_detect()`). Mission time will also drive features Gonzalo is specifying (protocol-practice and review bars that run down over time); do not build those until his spec is in an issue.
- Target path, about 6 actions (the Welcome's "Try it in 1 minute"): Welcome → NEXT → Main Menu → Demo controls: Reset demo, Advance mission 24 h → Check-in → alert from the mascot → Check-in chart with the personal baseline and bands → Simulate wait and repeat the measurement → Protocol: 2-3 short steps on the short branch (for example Mars, contact flight surgeon with the communication delay) → end.
- The demo story (astronaut, indicator, mission day, values) is written by Gonzalo with Edu; the data is generated by Fran.

**Content rules that follow from this:**
- **Short texts.** The mascot reads every protocol step and alert aloud: one or two short sentences per step.
- **Every protocol has a short branch** that the demo can follow in 3-4 nodes, **and** the complete flow for the judges. Both are real content from Edu, not shortcuts invented for the demo.
- Priority: one problem (SANS) complete end to end for the demo first; then muscle atrophy complete for the judges.

**The app for the judges:**
- It must be **complete**: both problems, every protocol path, Trends, all environments.
- It must be **self-explanatory**: the Welcome says in a few lines what the app does and how to try it in one minute, and the README explains what it does, what it does not do (it guides, it does not diagnose) and where every health value comes from.
- Each judge has their own data (section 5.5); a refresh starts again from the demo starting point.

## 16. Product specification (Gonzalo) and its overrides

`docs/ASTRONAUT_HEALTH_APP_SPEC.md` is the product reference for screens, navigation, bars, subjective issues, tutorials and the visual style. Read it before UI work. Where it says to reuse the repository (medical rules, severities, protocols), this file and `config/` win. **Decisions that override the spec (Ansel):**

1. **Mascot:** keeps subtitles and voice. Big and centred when alone, cards and buttons below it; small **on the left** only beside a chart or a flowchart (`mascot.beside()`); none on Trends and Tutorials (section 8, `docs/FRONTEND_MASCOT_LAYOUT.md`).
2. **Check-ins are grouped by test** (`config/checkins.json`, 5.6), not one card per indicator.
3. **Bars use the mission clock**, not real time, so the live demo can show them draining.
4. **Tutorials = practising a real protocol**: the same engine and flowchart, in practice mode (the episode dict has `"practice": true` and nothing is saved: no measurements, no detection, no episode). Each protocol has its own review interval (`tutorial_bar_full_days`).
5. **Data per astronaut**, not per (astronaut, mission): the environment only changes rules and branches, as before (spec section 5 allows keeping the repo behaviour).
6. The confirmation wait (`confirm_wait_min`) and the one-open-episode rule (section 10) stay; the Protocols screen shows the active episode and the pending alerts by severity.
7. **Welcome** uses conversational buttons (astronaut, then environment), no dropdowns and no NEXT.

**Before submission (after the Sunday 16:00 freeze; Ansel):** delete the internal Spanish documents in `docs/` (`ESTRUCTURA.md`, `Preparación del entorno · NASA Space Apps 2026.md`, `WORKFLOW.md`); complete every `TODO` in the README; make the repository public.
