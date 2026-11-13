# Astronaut Health Monitor · NASA Space Apps 2026

> Instructions for every AI coding agent working in this repo (Codex reads this file; Claude Code reads it through `CLAUDE.md`).
> If you are an AI agent: read this whole file before every task, and follow it over any other habit you have.
> To check that you have read it, the team may ask you "which project instructions do you know?": answer with the rules in section 9.

## 1. What this is

A Streamlit app for the NASA Space Apps 2026 challenge **"Create Health Monitoring Software for Astronauts on Space Missions"**.
It lets an astronaut record health measurements, detects anomalies against their **personal pre-flight baseline**, confirms them by asking for a **repeat measurement**, and then guides the astronaut through a **step-by-step protocol** (a flowchart) that depends on the problem, its severity and the mission environment (ISS, Moon, Mars...).

The app **guides, it does not diagnose**.

## 2. Stack

- Python 3.12, Streamlit, pandas, Plotly, numpy. pytest for tests.
- **Do not add any other library without asking.**
- Storage: CSV and JSON files in `data/`. No database server.
- Multipage Streamlit app: `app.py` + `pages/`.

## 3. Repository layout and owners

Each file has **one owner**. Only change files you were asked to change. If you need something from a file you do not own, use the contract in section 6 and, if it is not implemented yet, call the stub that is already there.

```
app.py                      Rol 3  Home: pick astronaut and environment, open-episode banner, Reset demo
pages/1_Check_in.py         Rol 5  Measurement form, trigger alert, confirmation step
pages/2_Protocol.py         Rol 6  Active protocol, step by step
pages/3_Trends.py           Rol 4  Charts with colour bands and personal baseline
core/models.py              Rol 3  Shared constants: severities, statuses, node types, paths
core/config.py              Rol 3  Load and validate config/*.json
core/data.py                Rol 4  Measurements, baseline, astronauts, episodes (read/write)
core/mission.py             Rol 4  Simulated mission clock
core/conditions.py          Rol 5  Shared condition evaluator (section 5)
core/triggers.py            Rol 5  Evaluate a new measurement against the problems
core/episodes.py            Rol 5  Open, confirm, dismiss, pending list, one-at-a-time rule
core/protocol_engine.py     Rol 6  Current step and advance with the astronaut's input
config/*.json               Rol 2  Health content (format owned by Rol 3)
config/protocols/*.json     Rol 2  Protocol flowcharts (format owned by Rol 3)
data/                       Rol 4  Runtime data; data/seed/ is the clean copy for Reset demo
scripts/generate_data.py    Rol 4  Generates pre-flight and simulated mission data
tests/                      Rol 3  Each builder adds tests for their own part
```

Roles: Rol 1 product and testing, Rol 2 science and health, Rol 3 architecture and integration, Rol 4 data and trends, Rol 5 detection, Rol 6 protocol execution.

## 4. Data formats

### 4.1 Measurements · `data/measurements.csv`

One row per measurement:

```
timestamp,astronaut,indicator,value,unit,phase,source
2027-04-10T08:00:00,a1,heart_rate,62,bpm,mission,manual
```

- `timestamp`: ISO 8601, mission time (see `core/mission.py`), no timezone.
- `indicator`: a key of `config/indicators.json`. Blood pressure is **two indicators**: `bp_systolic` and `bp_diastolic`.
- `phase`: `preflight` | `mission`.
- `source`: `simulated` | `manual` | `protocol`.

### 4.2 Baseline

For each astronaut and indicator: mean and standard deviation of the `preflight` measurements. Returned as `{"mean": float, "std": float, "n": int}`. z-score = (value − mean) / std.

### 4.3 Config files (in `config/`)

- `mission.json`: mission name, start time, default environment, astronauts.
- `indicators.json`: `{indicator_id: {name, unit, how_to_measure, why_it_matters, source}}`.
- `environments.json`: `{env_id: {name, gravity_g, comm_delay_min, source}}`. `comm_delay_min` is one-way.
- `problems.json`: `{problem_id: {name, description, hrp_risk, confirm_wait_min, protocol, triggers, source}}`.
  - `triggers`: list of `{severity, when, environments?}`. `when` is a condition (section 5). If `environments` is present, the trigger only applies there. If several triggers of the same problem match, the **highest severity** wins.
- `protocols/<problem_id>.json`: `{problem, start, nodes}` (section 7).

Problem ids starting with `_` (like `_example`) are **test fixtures**, never shown as real health content.

### 4.4 Episodes · `data/episodes.json`

```json
{
  "episodes": [
    {
      "id": "ep-0001", "astronaut": "a1", "problem": "problem_1", "environment": "mars",
      "status": "active", "severity_initial": "moderate", "severity": "severe",
      "trigger": {"indicator": "heart_rate", "value": 112, "z": 3.4, "measured_at": "2027-04-10T08:00:00"},
      "current_node": "remeasure", "vars": {"hr_after": 115}, "answers": {},
      "log": [{"at": "2027-04-10T08:12:00", "node": "do_action", "input": "done"}],
      "opened_at": "2027-04-10T08:05:00", "closed_at": null, "outcome": null
    }
  ],
  "pending": [
    {"astronaut": "a1", "problem": "problem_2", "severity": "mild", "indicator": "sleep_hours",
     "value": 5.0, "z": -2.3, "measured_at": "2027-04-10T08:00:00"}
  ]
}
```

Episode `status`: `pending_confirmation` → `active` or `dismissed`; `active` → `resolved` | `monitoring` | `handed_over` (set by an `end` node, also stored in `outcome`).

## 5. Condition language (`core/conditions.py`)

One evaluator for **both** triggers and protocol decisions. A condition is a JSON object:

| Keys | True when |
|---|---|
| `indicator` + `above` / `below` | latest value of that indicator is above / below the number |
| `indicator` + `z_above` / `z_below` | its z-score against the astronaut's baseline is above / below |
| `var` + `above` / `below` / `z_above` / `z_below` | same, for a value stored by a `measure` node (`save_as`) |
| `severity_at_least` / `severity_is` | current episode severity (order in `core/models.py`) |
| `environment_in` | current environment is in the list |
| `answer` + `equals` | the answer stored by a `question` node equals the value |
| `all` / `any` | list of conditions, combined with AND / OR |

`ctx` passed to `check(cond, ctx)`:
`{"astronaut", "environment", "severity", "vars", "answers", "latest": {indicator: value}}`.

## 6. Function contracts

Do not change a signature without asking Rol 3. Until a function is implemented it is a **stub** that returns fake data in the right format (marked `# STUB`).

```python
# core/models.py  (Rol 3)
SEVERITIES, EPISODE_STATUSES, OPEN_STATUSES, OUTCOMES, NODE_TYPES, PHASES, SOURCES
severity_rank(s) -> int
max_severity(a, b) -> str

# core/config.py  (Rol 3)
load_mission() -> dict
load_indicators() -> dict
load_environments() -> dict
load_problems(include_examples: bool = False) -> dict
load_protocol(problem_id: str) -> dict
validate_all(strict: bool = False) -> list[str]   # error messages; empty if OK

# core/data.py  (Rol 4)
load_astronauts() -> pd.DataFrame                  # columns: id, name, role
load_measurements(astronaut=None, indicator=None, phase=None) -> pd.DataFrame
add_measurement(m: dict) -> None                   # keys = columns of 4.1
get_baseline(astronaut: str, indicator: str) -> dict | None
z_score(astronaut: str, indicator: str, value: float) -> float | None
latest_values(astronaut: str) -> dict              # {indicator: last value}
load_episodes(astronaut: str | None = None) -> list[dict]
save_episode(episode: dict) -> None                # create or replace by id
get_open_episode(astronaut: str) -> dict | None    # pending_confirmation or active
load_pending(astronaut: str | None = None) -> list[dict]
save_pending(items: list[dict]) -> None            # replaces the whole pending list
reset_demo() -> None                               # copy data/seed/* over data/

# core/mission.py  (Rol 4)
now() -> datetime
advance(hours: int = 24) -> list[dict]             # new simulated measurements now visible

# core/conditions.py  (Rol 5)
check(cond: dict, ctx: dict) -> bool

# core/triggers.py  (Rol 5)
evaluate(measurement: dict, environment: str) -> list[dict]
# one item per matching problem: {"problem", "severity", "indicator", "value", "z"}

# core/episodes.py  (Rol 5)
on_new_measurement(measurement: dict, environment: str) -> dict | None
# Single entry point, called by Check-in and after mission.advance().
# Applies confirmation and the one-open-episode-per-astronaut rule; returns the open episode, if any.
confirm(episode_id: str, measurement: dict) -> dict   # -> active (severity from this measurement) or dismissed
get_pending(astronaut: str) -> list[dict]

# core/protocol_engine.py  (Rol 6)
current_step(episode: dict) -> dict      # the node, with id and display-ready text
submit(episode: dict, user_input: dict | None) -> dict
# Advances one or more nodes (decision and set_severity nodes run without input),
# stores measurements (source="protocol"), updates severity, closes on `end`, saves the episode.
```

Streamlit session state (created by `app.py`): `st.session_state["astronaut"]`, `st.session_state["environment"]`.

## 7. Protocol flowcharts (`config/protocols/<problem_id>.json`)

```json
{"problem": "problem_1", "start": "first_node", "nodes": {"first_node": {"type": "...", "...": "..."}}}
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
`config/protocols/_example.json` uses every node type and is the fixture for building and testing the engine.

## 8. Behaviour rules

1. Triggers are evaluated only on **new** measurements (manual, protocol or revealed by `mission.advance()`). Simulated history never opens episodes.
2. When a trigger fires and the astronaut has no open episode: create an episode with status `pending_confirmation` and ask to **repeat the same indicator** after `confirm_wait_min` (the demo has a "Simulate wait" button). If the repeat also triggers, the episode becomes `active` with the severity given by the repeat; otherwise `dismissed`.
3. **One open episode per astronaut.** Other triggers go to `pending`. When the episode closes, offer the most severe pending one; it goes through confirmation again.
4. Severity starts with the trigger and can change only through `set_severity` nodes.
5. Measurements taken inside a protocol do not open new episodes for the same problem.

## 9. Rules for AI agents

- **English everywhere**: UI text, code, comments, commit messages, docs that the jury can see.
- **Never invent medical values.** Every threshold, range, wait time or health advice comes from `config/` files written by Rol 2. If a value you need is missing or says `TODO`, stop and say so; do not fill it in.
- **Touch only the files you were asked to.** Never edit another owner's file, not even "a small fix": describe the change and let the owner do it.
- **Small changes.** One feature or fix per request. Do not rewrite whole files. Do not reorganise the project.
- **Keep the contracts** in section 6. Do not rename functions, parameters, JSON keys or CSV columns.
- Pages (`app.py`, `pages/`) **never read or write files directly**: they only call `core/`.
- No new libraries, no new top-level folders, no secrets or API keys in the code.
- Add a test in `tests/` when you add logic in `core/`. Keep `pytest` green.
- **Mark AI-generated code.** Every new file starts with a header comment: `# AI-assisted: generated with <tool> and reviewed by <role>.` (NASA Space Apps requires AI-generated code to be acknowledged in text and metadata).
- At the end of every task, say **which files you changed and how to test it** in one or two lines.

## 10. Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
pytest
python -m core.config      # validates config/ and prints errors
```

## 11. Git workflow

- `main` always starts. Run the app and `pytest` before every push.
- One branch per task: `rolN/short-description` (e.g. `rol5/confirmation-step`). Open a pull request; Rol 3 reviews and merges.
- Small commits with messages that say what changes. Commit every time something works.
- Integrations: Saturday 14:00 and 19:00 (first deploy), Sunday 13:00. Feature freeze Sunday 16:00.
