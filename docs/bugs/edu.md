<!-- AI-assisted: generated with Codex and reviewed by Edu. -->

# Edu: health-content bug report

Prepared on 15 November 2026 against `main` commit `0baa36e`. This document collects all unresolved findings from the health-content audit; it is not a guarantee that no other bugs exist. No application behavior was changed to prepare it.

Scope: indicator definitions and measurement domains, problem rules, subjective symptoms and alarms, check-in links and timers, environment values, and the medical material used in both protocols. Protocol implementation belongs to Javi under the current AGENTS.md; findings affecting it are included because they depend on Edu's material.

Priority: **P2** = normal-priority workflow/content issue; **P3** = lower-priority issue with limited current exposure. Medical-content concerns below require a decision, rather than being presented as proven clinical defects.

## Findings at a glance

| ID | Priority / status | Screen or component | Reproduce | Expected | Actual | Owner / next step |
| --- | --- | --- | --- | --- | --- | --- |
| EDU-01 | P2, reproduced workflow gap | Protocols: SANS `w_correction`, muscle `w_exercise` | Reach the action while unable to obtain prescribed lenses or specialist review. | A truthful way to report that the action cannot be completed, preserving an appropriate open task. | Only **Done** is offered; the engine rejects `action="cannot"`. | Javi implements; Edu supplies any additional medical instruction. |
| EDU-02 | P3, reproduced domain gap | Temperature validation | Call `measurement_errors()` with temperature -500 and its configured Celsius unit. | Reject a physically impossible temperature. | Returns `[]`, meaning valid. Temperature has no current check-in card, so this is an API/configuration gap. | Edu: source and define the physical domain; no invented clinical range. |
| EDU-03 | P2, medical wording concern | SANS `w_correction` | Read the treatment-related sentence and its cited consensus. | Preserve the source's distinction between investigational countermeasures and drugs with unacceptable in-flight risks. | Acetazolamide is grouped with options described as "for clinicians or research" without the source's flight-specific restriction. | Edu decides wording; Javi applies it to the protocol. |
| EDU-04 | P2, coverage concern | Check-in: `VIS_01` near-vision complaint | Inspect its linked check-ins and their measurement instructions. | A clear explanation of how a near-vision complaint is assessed or referred. | It accelerates only `visual_acuity`, whose instructions specify prescribed distance lenses; no separate near-acuity measurement is defined. | Edu and Ansel decide coverage/mapping; no automatic remapping proposed. |
| EDU-05 | P3, confirmed existing issue | Protocol narration | Count characters in every real protocol node's `text`. | Meet the approximately 200-character limit requested in #223 while preserving medical meaning. | Six steps contain 206-213 characters. | Already tracked in [#223](https://github.com/ansel-07/nasa-health-monitor/issues/223); Edu wording, Javi implementation. |

## Reproduction and evidence

### EDU-01: actions cannot be declined

Locations: [SANS `w_correction`](../../config/protocols/sans.json), [muscle `w_exercise`](../../config/protocols/muscle_atrophy.json), and [Protocol page](../../pages/2_Protocol.py).

For SANS, follow the watch route with no red flags, report mild focusing difficulty, and answer that required lens strengths are not beyond available capacity. For muscle monitoring, continue through the clinician contact/review to the exercise-specialist action. If the real-world action cannot be completed, neither step provides an alternative to **Done**. The episode remains active if the user stops there; the bug is the missing way to record the obstacle, not automatic closure.

Both nodes lack `next_if_cannot`. In the audit, isolated Streamlit page checks displayed **Show whole protocol** and **Done**, with no **I can't**. Submitting `{"action": "cannot"}` directly produced `ValueError: Action must be 'done' or a configured 'cannot' route.` This finding concerns these two watch actions, not the separately approved urgent-stop change in PR #256.

### EDU-02: temperature has no physical lower bound

Location: [`temperature` in indicators.json](../../config/indicators.json). Run from the repository root with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -c "from core import config; unit = config.load_indicators()['temperature']['unit']; print(config.measurement_errors({'indicator': 'temperature', 'value': -500, 'unit': unit}))"
```

Actual output: `[]`. This is below absolute zero for ordinary body-temperature measurement. [NIST's temperature definitions and conversion](https://www.nist.gov/pml/owm/si-units-temperature) establish the physical distinction; they do not supply a clinical body-temperature range. Any configuration correction must be sourced and selected by Edu.

### EDU-03: acetazolamide wording needs a decision

Location: [`sans.json`, `w_correction.text`](../../config/protocols/sans.json). The app discourages self-treatment, and `w_end` also says not to start medicines from the app. Nevertheless, the earlier grouping can imply that clinician involvement alone makes every listed option suitable in flight. That implication is the audit concern; the app does not prescribe a dose or administer treatment.

The cited [Gew et al. 2026 consensus, Emerging therapeutic strategies](https://pmc.ncbi.nlm.nih.gov/articles/PMC13462731/) describes acetazolamide adverse effects and considers those risks unacceptable during long-duration spaceflight. This section was read during the preceding audit; a repeat retrieval encountered a publisher/archive browser challenge. Edu should decide how explicitly to preserve that restriction in the short astronaut-facing text.

### EDU-04: near-vision coverage is unclear

Locations: [`subjective_issues.json`, `VIS_01`](../../config/subjective_issues.json), [`checkins.json`, `visual_acuity`](../../config/checkins.json), and both `visual_acuity_*` definitions in [indicators.json](../../config/indicators.json).

`VIS_01.check_ins` is `["visual_acuity"]`. Its question concerns nearby letters, while both linked indicator instructions specify prescribed distance lenses. [NASA OCHMO-MTB-001, page 9](https://www.nasa.gov/wp-content/uploads/2024/02/ochmo-mtb-001-sans.pdf) lists distance and near acuity separately. The inference requiring review is that the configured test does not establish near-vision function. The symptom remains recorded; it is not silently deleted or converted into a diagnosis. Existing links explicitly document Ansel's prototype mapping decision, so changing the mapping requires coordination.

### EDU-05: six long protocol lines

Character counts include spaces and punctuation:

| Protocol | Node | Characters |
| --- | --- | ---: |
| SANS | `w_acuity` | 206 |
| SANS | `w_correction` | 213 |
| SANS | `w_end` | 210 |
| Muscle atrophy | `w_red_flags` | 213 |
| Muscle atrophy | `w_end` | 211 |
| Muscle atrophy | `u_end` | 209 |

These are modest overruns of an approximate target, not a runtime failure. Shortening must retain warning signs, limits and sources.

## Fixed or intentionally excluded

- Measurement domains requested in #245 were merged in [PR #250](https://github.com/ansel-07/nasa-health-monitor/pull/250); EDU-02 is the remaining temperature-specific gap.
- Missing new-double-vision wording in SANS was fixed in [PR #252](https://github.com/ansel-07/nasa-health-monitor/pull/252).
- Protocol source citations were updated in [PR #235](https://github.com/ansel-07/nasa-health-monitor/pull/235).
- The `u_help` removal and single-exit urgent stop in [PR #256](https://github.com/ansel-07/nasa-health-monitor/pull/256) were explicitly approved by Edu and merged. They are not listed as outstanding bugs.
- Synthetic bar timers, explicitly qualified confirmation estimates, zero-SD grade baselines evaluated by raw grade rules, and separately stored left/right eyes are documented design choices, not findings here.

## Validation and limits

On the report's base revision, strict configuration validation returned no errors and the focused suite below passed **174 tests**. The temperature acceptance, missing refusal routes, near-vision links and six character counts were rechecked directly. The preceding audit also passed 267 relevant tests, checked 107 terminating protocol paths across environments and concern states, and checked eye-rule symmetry, configured domain boundaries and one check-in per used indicator. Those results do not establish clinical safety or guarantee exhaustive bug coverage.

To repeat the focused automated checks on this revision:

```powershell
.\.venv\Scripts\python.exe -m core.config --strict
.\.venv\Scripts\python.exe -m pytest tests/test_health_config.py tests/test_protocol_content.py tests/test_measurement_validity.py tests/test_config.py -q
```

Passing tests do not refute these findings: valid configuration and the existing happy-path tests permit the missing routes and wording concerns. This report changes documentation only and introduces no medical values, treatment instructions or application fixes.
