# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Generate simulated pre-flight and mission data. Owner: Rol 4.

Usage (from the repo root):  python -m scripts.generate_data

STUB. Rol 4 writes the generator:
- one row per measurement, columns of AGENTS.md section 4.1;
- preflight phase: enough days per astronaut to compute a baseline;
- mission phase: trend + normal noise + the anomalies of the demo scenario
  (decided with Rol 1; values reviewed by Rol 2);
- use numpy.random.default_rng(seed) so the data is reproducible;
- write data/measurements.csv AND the same file in data/seed/ (for Reset demo).
"""


def main() -> None:
    raise NotImplementedError("Rol 4: write the generator (see the docstring).")


if __name__ == "__main__":
    main()
