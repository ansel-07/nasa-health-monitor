# TODO: Project name

> TODO: one-sentence tagline.

Built for the [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/) — challenge
[**Create Health Monitoring Software for Astronauts on Space Missions**](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/).

> **Prototype, not a medical device.** This app guides astronauts and explains; it does not diagnose. Diagnosis belongs to the crew medical officer and flight surgeons.

## Links

- Live app: TODO
- Demo (30 s video or 7 slides): TODO
- Space Apps project page: TODO

## The problem

TODO: why astronauts need to assess their own health on long missions (hazards, distance from Earth, communication delay).

## What it does

TODO: the user's journey in a few lines.

## Meet the mascot

TODO: name, look and personality of the mascot that narrates the app.

## How it works

TODO: short explanation of the flow: measurements → personal baseline → trigger → confirmation → protocol by problem, severity and environment.
Architecture and contracts: see [`AGENTS.md`](AGENTS.md).

## Health indicators and problems

TODO: table of indicators and of the problems covered, each with its source.

## NASA data and resources used

TODO: which NASA resources were used and for what.

## Other data and references

TODO: every external dataset, code, text and image used, with its source.

## AI usage

TODO: which AI tools were used, by whom and for what (code generation, review, text). AI-generated code is marked with a header comment in each file.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pytest`

## Project structure

```
app.py, pages/      Streamlit screens
core/               logic (data, triggers, episodes, protocol engine)
config/             health rules, environments, problems and protocols (JSON)
data/               measurements, astronauts and episodes (CSV/JSON); data/seed/ for Reset demo
scripts/            simulated data generator
tests/              pytest tests
```

## Decisions log

- TODO

## Limitations and future work

- **Baseline quality.** Baseline-relative criteria use the mean and standard deviation of the pre-flight measurements of each astronaut and indicator (at least two sessions, non-zero spread). When no valid baseline exists, the app says the indicator cannot be evaluated yet and never reports it as normal. A complete model (explicit "not evaluable" results through every rule, reference quality metadata and automatic re-evaluation) is future work.

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
