# SpaceDoc

> Your health, guided through every mission.

Built for the [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/) — challenge
[**Create Health Monitoring Software for Astronauts on Space Missions**](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/).

> **Prototype, not a medical device.** This app guides astronauts and explains; it does not diagnose. Diagnosis belongs to the crew medical officer and flight surgeons.

## Links

- Live app: https://nasa-health-monitor-jyjqxq9oyta7gece258ben.streamlit.app/
- Slides (7 slides, live demo): TODO
- Space Apps project page: TODO

## The problem

On long missions astronauts are far from a hospital and, beyond low Earth orbit, from real-time help: a one-way signal between Mars and Earth takes from about 3 to 22 minutes ([NASA](https://science.nasa.gov/blog/speaking-percys-language-how-to-talk-so-perseverance-will-listen/)). The crew has to notice early changes in their own health and respond in a safe, structured way, often before anyone on Earth can answer.

SpaceDoc focuses on two risks studied by NASA's Human Research Program: [Spaceflight Associated Neuro-ocular Syndrome (SANS)](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-spaceflight-associated-neuro-ocular-syndrome/), changes in the eyes and vision, and [reduced muscle size, strength and endurance](https://www.nasa.gov/directorates/esdmd/hhp/muscle-risk/). Both change gradually, so the useful question is not only "is this value normal?" but "has it changed from this astronaut's own pre-flight baseline, and what should they do next?"

## What it does

The astronaut chooses who they are and where the mission is (ISS, Moon or Mars). From the Main Menu they record health check-ins, review their trends and practise protocols. Each measurement is compared with **their own pre-flight baseline**; an anomaly is confirmed with a **repeat measurement** before anything else happens, and a confirmed one opens a **step-by-step protocol** adapted to the problem, its severity and the mission environment (for example, the communication delay with Earth on Mars). Progress bars remind the astronaut when a check-in or a protocol practice is due. A simple animated face narrates every step with subtitles and an optional voice.

### Try it in 1 minute

1. Choose **Astronaut A** and **International Space Station**, then **NEXT**. In Main Menu → *Demo controls*, press **Reset demo**. You will explore fictional, synthetic measurements.
2. Press **Advance mission 24 h** to reveal an ocular measurement alert. Open **Check-in** to compare it with your personal pre-flight baseline.
3. Use **Simulate wait** and repeat the flagged measurement with the demo value (**360** µm) to confirm the anomaly.
4. Open **Protocols** and follow the guidance through to medical follow-up. SpaceDoc guides you; it does not diagnose.

## Meet the mascot

TODO: name, look and personality of the mascot that narrates the app.

## How it works

Measurement → **personal baseline** (pre-flight mean and spread of each astronaut) → **symptom levels** (watch / concern) from rules written by our health lead with their sources → **problem state** → **confirmation** with a repeat measurement → **protocol** (a flowchart with steps, questions, measurements and contacts with the crew medical officer or flight surgeons). Simulated mission time drives the demo: advancing it reveals new synthetic measurements and drains the progress bars.
Architecture and contracts: see [`AGENTS.md`](AGENTS.md).

## Health indicators and problems

TODO: table of indicators and of the problems covered, each with its source.

## NASA data and resources used

TODO: which NASA resources were used and for what.

## Other data and references

TODO: every external dataset, code, text and image used, with its source.

## AI usage

AI-generated code is marked with an `AI-assisted` header comment in each file. Which AI tools each team member used, and for what:

- **Fran (data and trends):** Claude Code for code and tests of the data layer, mission clock, charts, Trends page, activity bars and data generator, and for drafting GitHub issues; every change was reviewed and run by Fran before merging.
- **Javi (protocol execution):** Claude Code and Codex for code and tests of the protocol engine, the Protocols and Tutorials screens, the flowchart and the protocol test sandbox, and for drafting GitHub issues and pull requests; every change was reviewed and run by Javi before merging.
- **Juan Carlos (detection):** Codex assisted with the condition evaluator, trigger evaluation, episode lifecycle, Check-in UI, automated tests, and GitHub issue and pull-request drafts; Juan Carlos personally reviewed the generated code and tests, with integration review through the repository's pull-request workflow.
- **Gonzalo (product, coordination and testing):** Codex to record his product decisions, demo story and timing confirmations as GitHub issue comments (#34, #39, #99); he decided their content.

## Run locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Tests: `python -m pytest` · Config check: `python -m core.config`

## Project structure

```
app.py              entry point and navigation
pages/              screens: Welcome, Main Menu, Check-in, Protocols, Trends, Tutorials
core/               logic: data, baseline, detection, episodes, protocol engine, bars, mascot
config/             health rules, check-ins, environments, problems and protocols (JSON)
data/seed/          synthetic demo data copied into every browser session
scripts/            synthetic data generator
docs/               product specification and demo-data notes
tests/              pytest tests
```

## Decisions log

- **Personal baseline, not population ranges:** each astronaut is compared with their own pre-flight data.
- **Confirm before acting:** an anomaly needs a repeat measurement before a protocol starts.
- **One open alert per astronaut;** others wait in a queue ordered by severity.
- **Guides, does not diagnose:** every threshold, step and text comes from sourced configuration; concerning findings lead to medical review.
- **Each browser session has its own copy of the demo data,** so several judges can try the app at once.
- **Simulated mission clock** for measurements, alerts and progress bars, so a live demo can show days passing.

## Limitations and future work

- **Baseline quality.** Baseline-relative criteria use the mean and standard deviation of the pre-flight measurements of each astronaut and indicator (at least two sessions, non-zero spread). When no valid baseline exists, the app says the indicator cannot be evaluated yet and never reports it as normal. A complete model (explicit "not evaluable" results through every rule, reference quality metadata and automatic re-evaluation) is future work.

- **Synthetic data.** All measurements in the demo are fictional and synthetic; they are not astronaut physiology.
- **Two configuration formats.** The code still accepts the first rule format (`triggers`) next to the symptom-based one used by all real content; removing it is future work.

## Team

| Name | Role |
|---|---|
| Gonzalo | Product, coordination and testing |
| Edu | Science and health |
| Ansel | Architecture, integration and mascot |
| Fran | Data and trends |
| Juan Carlos | Anomaly detection |
| Javi | Protocol execution |

## License

[MIT](LICENSE)
