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

## Team

TODO: names and roles.

## License

[MIT](LICENSE)
