<!-- AI-assisted: generated with Codex; human review pending. -->

# Synthetic demo data handoff

Status: proposed parameter specification for an explicitly synthetic software
benchmark, reviewed against primary sources on 2026-11-14 for issue #36.
It supplements the research table in #35/#36; it does not supply validated
healthy-astronaut population or daily-variability parameters. It is not a physiological model,
an astronaut reference population, or a validated disease trajectory. The
benchmark does not by itself complete clinical configuration or deployment.

## 1. Scope and provenance

Simulate three indicators: left-eye peripapillary total retinal thickness (TRT),
right-eye TRT, and muscle force. Keep all other indicator definitions in the
catalogue, but do not generate unsupported distributions for them. The original
heart_rate, sleep_hours, mood and example entries must remain intact.

The earlier Edu handoff in [#43](https://github.com/ansel-07/nasa-health-monitor/issues/43#issuecomment-6879885382)
and the existing configuration tests attribute these worked examples to
`guia_breve_umbrales_atrofia_SANS (1).pdf` (2026-11-14):

- Page 1: force baseline mean 500 N and sample SD 25 N.
- Page 2: TRT baseline mean 300 micrometres and sample SD 5 micrometres.

The PDF is not stored in this repository; this review does not claim a new
inspection of its pages. These examples are synthetic anchors, not measured
healthy-astronaut averages. Applying the TRT
example independently to each eye is a benchmark choice, not evidence that the
eyes have identical anatomy or independent physiological noise.

## 2. Complete generator input

Use this block with the existing `scripts.generate_data.generate()` and
`check_params()` functions. Fran owns integration into the script and seed data;
this document adds no production API or configuration schema.

```python
SEED = 2027
PREFLIGHT_DAYS = 14
MISSION_DAYS = 10
DEMO_DAY = 1
MEASURE_HOUR = 8

INDICATOR_PARAMS = {
    "peripapillary_trt_left": {
        "mean": 300.0,
        "sd": 5.0,
        "person_sd": 0.0,
        "trend_per_day": 0.0,
        "decimals": 1,
    },
    "peripapillary_trt_right": {
        "mean": 300.0,
        "sd": 5.0,
        "person_sd": 0.0,
        "trend_per_day": 0.0,
        "decimals": 1,
    },
    "muscle_strength": {
        "mean": 500.0,
        "sd": 25.0,
        "person_sd": 0.0,
        "trend_per_day": 0.0,
        "decimals": 1,
    },
}

ANOMALIES = [
    {
        "astronaut": "a1",
        "indicator": "peripapillary_trt_left",
        "day": 1,
        "value": 360.0,
    },
    {
        "astronaut": "a2",
        "indicator": "muscle_strength",
        "day": 2,
        "value": 390.0,
    },
]
```

| Parameter | Meaning and justification |
| --- | --- |
| `mean`, `sd` | Parameters of generated synthetic observations, using the PDF's worked examples. `sd` is not an empirical estimate of daily astronaut variability. |
| `person_sd = 0` | Disable random offsets between the three fictional astronauts. This is a fixed benchmark design, not a claim that real people have zero between-person variability. Finite sampled baselines will still differ. |
| `trend_per_day = 0` | Hold the synthetic background stationary so injected anomalies can be tested independently. This is a deliberate simulation policy, not missing evidence replaced with a physiological zero. |
| `decimals = 1` | Output precision for this software fixture; not instrument accuracy. |
| No `min` or `max` | No clinical hard bounds or clipping are asserted. These optional keys are omitted, not guessed. Validate the generated values instead. |
| 14 preflight days | Software sampling window inherited from the generator. It is not a validated minimum duration for a stable clinical baseline. |
| 10 mission days | Test horizon, not a claim that either disease develops within ten days. A time-stamped injected observation exercises detection; it does not simulate onset or recovery. |
| `SEED = 2027` | Reproducible benchmark with the current generator, indicator order, astronauts a1/a2/a3, and environment. Changing any of these requires revalidation. |
| 360 micrometres | Synthetic left-eye case chosen above the PDF's +55 micrometre review boundary, with margin for the sampled reference. It is not a clinical recommendation or a reported patient observation. |
| 390 N | Synthetic muscle-force case chosen below 80% of the nominal 500 N example. Verify against the sampled personal baseline rather than assuming it is exactly 500 N. |

The benchmark uses a single fixed synthetic force task for `muscle_strength`,
not pooled muscles, sides, methods or instruments. A future empirical simulator
must first select and document a real task. Both eye indicators use the same
synthetic TRT definition and preserve eye identity throughout.

## 3. Time, anomaly and confirmation checks

Use `seed_clock(start, DEMO_DAY)` from the current generator. With this proposed
benchmark's `DEMO_DAY = 1`, the seed starts at 2027-04-01 at 00:00, before the
first observation at 08:00. Another demo day can also work if the seed clock and
anomaly move together; Gonzalo owns that story choice. At reset:

1. Preflight observations are available for computing each personal reference.
   Future mission observations must stay hidden.
2. One advance reveals nine new observations, including a1's left-eye 360.0
   micrometre reading. The right eye remains a separate observation.
3. A synthetic confirmation of the same indicator with value 360.0 remains above
   the +55 micrometre criterion. Apply the configured estimated repeat timer; it
   is not part of the observation-generation model.
4. A second advance reveals a2's 390.0 N force reading. Repeating 390.0 N remains
   below 80% of that astronaut's sampled baseline.

This is a proposed technical acceptance scenario, not an attempt to replace
Gonzalo's final pitch story. No clinical-priority symptoms are assigned to these
numerical anomalies. A concerning number alone must not be labelled a medical
urgency. The real production evaluator, clock and episode lifecycle are exercised
by the accompanying tests; this does not establish diagnostic performance.

The right-eye observation can also return the already-positive SANS state because
the problem uses the latest values of both eyes. This does not mean the right eye
crossed a threshold. The one-open-episode rule prevents a duplicate SANS episode.

With the current generator and the exact block above, compute the references from
the generated preflight rows. Expected anchors (rounded here for reporting):

| Case | Sampled personal mean | Sample SD | Injected value | Criterion result |
| --- | ---: | ---: | ---: | --- |
| a1 left TRT | 297.835714 micrometres | 4.183412 micrometres | 360.0 micrometres | Delta +62.164286 micrometres, above the inclusive +55 boundary |
| a2 force | 518.750000 N | 23.870121 N | 390.0 N | 75.1807% of personal reference, below the strict 80% boundary |

Validate full-precision results in memory. Do not manufacture exact reference
values by rounding or overwrite preflight measurements to make a case pass.
Sampled reference values and anomaly margins change if the input order changes.

## 4. Corrections to the earlier evidence handoff

The earlier table was a source inventory, not ready-to-run generator input.
It mixed candidates with different methods and left required fields unresolved.
Keep that inventory for research, but do not copy it into `INDICATOR_PARAMS`.

| Earlier problem | Correction |
| --- | --- |
| Knee-extension torque supplied for a force indicator | Exclude the N m values; no guessed lever arm or force conversion. The synthetic fixture stays in N. An empirical force alternative now exists below. |
| Population SD, measurement error and daily variability conflated | Keep them as distinct statistics. Neither population SD nor a within-session OCT repeatability statistic is treated as an astronaut daily SD. |
| Unspecified muscle/site or ocular region | Use one explicitly fixed synthetic task/measurement definition. No cross-device or cross-region empirical pooling is performed. |
| Mixed clinical cohorts and healthy references | No study participant is treated as a fictional astronaut or as a generic healthy-astronaut reference. |
| Unsupported daily disease trends | Use an openly declared stationary software fixture and explicit anomaly overrides. No clinical trajectory is inferred from endpoint differences. |
| No executable scenario | The block now supplies every required generator parameter and two reproducible test cases; the first is revealed on the first advance. |
| Missing values for every catalogue indicator | Limit this benchmark to the three fully specified indicators; do not insert unsupported values for the remaining catalogue. |

## 5. Newly verified empirical alternatives and their limits

These are research alternatives, **not the generator inputs above**.

### Force measured in N

[Aben et al., Sports 2020, Table 2](https://www.mdpi.com/2075-4663/8/5/73)
reports isometric mid-thigh pull peak force: week-one mean 2593.47 N, group SD
288.46 N, and between-session typical error 112.46 N. The repeated sessions were
one week apart in academy rugby players. These quantities fix the N-versus-N m
mismatch, but do not establish astronaut norms, daily variability or an inflight
task-equivalence guarantee. The group SD must not be copied into daily `sd`, nor
must typical error be silently relabelled a complete daily physiological SD.

### Circumpapillary OCT repeatability

[Kita et al., PLOS ONE 2015, OCT methods and Table 2](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144721)
studies NIDEK RS-3000 circumpapillary total retinal thickness on a 3.45 mm circle,
with three scans about five minutes apart. It reports global repeatability CV
0.60% and reproducibility coefficient 5.95 micrometres. This supplies real
same-session measurement evidence, not a daily physiological series, and does
not establish equivalence to the Spectralis protocol underlying the SANS criteria.

For a future empirical model, obtain matching repeat-session data for the selected
task, instrument and region, document the sampling interval and model uncertainty,
and retain separate eyes/sites. Do not use case reports as population norms or
replace missing trends with an unlabelled zero.

## 6. Integration and release boundaries

Fran can validate or copy the generator block without changing its signature or
adding a library. This delivery does not edit Fran's script or runtime/seed data.
The values should be described as **synthetic benchmark observations** in any
public demonstration. They cannot support claims of diagnostic accuracy or
physiological prediction.

Generation and lifecycle checks run in isolated temporary storage through the
real generator and core APIs. They cover baseline calculation, a single advance,
two anomaly cases, confirmation, watch protocols and eye independence. They do
not test the deployed application or authorize clinical use.

Before treating the final deployed demo as complete: integrate the agreed story
with Gonzalo, have Fran generate the seed, confirm the reference-dependent rules
against the real evaluator, and run the full detection-confirmation-protocol path.
This document does not change the generator, runtime files, seed or medical rules.
An evidence/documentation PR can be reviewed without activating the benchmark.
Keep #36 open if its acceptance still requires empirical healthy-astronaut means,
daily SDs and between-astronaut distributions: those are not delivered here.

## 7. Scientific review and acceptance

Primary sources checked on 2026-11-14:

| Source | Supported interpretation | Does not validate |
| --- | --- | --- |
| [NASA muscle strength standard, 4.6.2, V1 4024](https://www.nasa.gov/reference/4-0-human-performance/) | In-mission strength retention at or above 80% of baseline. The injected force is below this relative criterion. | A generic 500 N baseline, 25 N daily SD, a particular muscle task, or an atrophy diagnosis. |
| [NASA SANS 2023 clinical update, p. 1](https://ntrs.nasa.gov/api/citations/20220014606/downloads/Brunstetter%20-%20IWS%202023%20SANS%20Clinical%20Update%20-%20Abstract%20-%2023Sep22.pdf) | TRT changes of at least 20 and 55 micrometres distinguish early and concerning structural findings. | The synthetic 300/5 distribution, daily OCT sampling, a permanent-damage boundary or automatic medical urgency. |
| [Brunstetter et al., JAMA Ophthalmology 2024, Results/Figure 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC11273286/) | One astronaut had eye-specific preflight TRT of 401/404 micrometres and peaks at flight days 84/126. | A population baseline, linear daily disease trend, or onset of SANS in this ten-day software horizon. |
| [Patel et al., JAMA Ophthalmology 2018, Table 2](https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2667551) | In the BMO-to-250-micrometre annulus, preflight cohort mean/SD were 362/38 micrometres, with observed range 272-420. | Treating 38 as daily within-person SD or treating the fixture's 300 as the typical astronaut mean. The region/device must match before using cohort data. |
| [Pardon et al., JAMA Ophthalmology 2022, cohort table](https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2797831) | A different cohort reports preflight mean 392.0 micrometres with SE 5.8, for the BMO-250 region. | Confusing SE with SD, or pooling cohorts and eyes to fabricate daily variation. |

[Macias et al., JAMA Ophthalmology 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7118682/)
reports early structural changes, including at flight day 10 in an outer TRT
annulus. It would therefore also be incorrect to claim that ocular changes cannot
occur within ten days. This does not establish our +55-micrometre day-one event
or a constant daily trend: the measurement region, outcome and time course differ.

The means, daily SDs, between-person spread and trends required for a physiological
simulator remain unestablished for the selected task/device/site. The reviewed
sources support the criterion semantics and limitations, not the statistical
distribution of this fixture. Scientific source review and software validation
must not be described as clinical validation of the generator.

The generator currently samples independent Gaussian noise without estimating
autocorrelation or inter-eye dependence. At a one-sided z <= -2 watch threshold,
even a stationary background can cross by chance (about 2.3% with a known normal
reference; a sampled reference changes that probability). Do not tune a seed and
then claim a measured false-alert rate. Extra watch results across the full horizon
must be reported and do not establish disease.

Run `.venv/Scripts/python.exe -m pytest tests/test_demo_data_handoff.py -q`.
The tests read the exact documented parameter block, so changing its seed, order,
mission days or scenario requires revalidation. A passing result establishes a
reproducible software scenario with scientifically traceable criteria, while
population validity and the final demo story remain separate acceptance items.
