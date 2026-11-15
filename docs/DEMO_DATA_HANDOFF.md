<!-- AI-assisted: generated with Codex and reviewed by Edu. -->

# Synthetic demo data handoff

Status: Edu accepts design A (declared synthetic data) on 2026-11-14, conditional
on human plausibility. Edu subsequently specifies all fourteen indicators for the demo. This provides
the full parameter table and plausibility checks; Gonzalo approved the a1/ISS
left-TRT story in #34 (recorded on #35). It is reviewed against primary sources for issue #36.
It supplements the research table in #35/#36; it does not supply validated
healthy-astronaut population or daily-variability parameters. It is not a physiological model,
an astronaut reference population, or a validated disease trajectory. The
benchmark does not by itself complete clinical configuration or deployment.

The attribution fix for [#91](https://github.com/ansel-07/nasa-health-monitor/issues/91)
is integrated. The batch-advance regression is now required to pass, together
with detection, same-indicator confirmation and watch protocols in all three
environments. The parameter handoff completes Edu's contribution to #36;
Fran owns generator/seed integration and Gonzalo owns the final presentation.

## 1. Scope and provenance

Simulate all fourteen indicators used by SANS and muscle atrophy: six muscle
measurements and four ocular measurements for each eye. Catalogue cleanup is a
separate task (#81); example fixtures are never simulated.

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

## Currently integrated fixture (three indicators)

This is the earlier #83 block currently used by Fran's generator and seed.
It is retained here so the existing generator contract test can verify the
integrated state. It is superseded for the #36 handoff by the complete fourteen-
indicator proposal in section 2, including persistent anomalies. Do not describe
the old isolated anomalies as recovery or as the final approved dataset.

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
    "optic_disc_edema_grade_left": {"mean": 0, "sd": 0, "person_sd": 0, "trend_per_day": 0, "min": 0, "max": 0, "decimals": 0},
    "optic_disc_edema_grade_right": {"mean": 0, "sd": 0, "person_sd": 0, "trend_per_day": 0, "min": 0, "max": 0, "decimals": 0},
    "refraction_left": {"mean": -1.0, "sd": 0.05, "person_sd": 0, "trend_per_day": 0, "decimals": 2},
    "refraction_right": {"mean": -1.0, "sd": 0.05, "person_sd": 0, "trend_per_day": 0, "decimals": 2},
    "visual_acuity_left": {"mean": 0.0, "sd": 0.03, "person_sd": 0, "trend_per_day": 0, "decimals": 2},
    "visual_acuity_right": {"mean": 0.0, "sd": 0.03, "person_sd": 0, "trend_per_day": 0, "decimals": 2},
    "muscle_area": {"mean": 10.0, "sd": 0.2, "person_sd": 0, "trend_per_day": 0, "decimals": 2},
    "muscle_power": {"mean": 186.0, "sd": 8.0, "person_sd": 0, "trend_per_day": 0, "decimals": 1},
    "muscle_endurance": {"mean": 14.4, "sd": 1.0, "person_sd": 0, "trend_per_day": 0, "min": 0, "decimals": 0},
    "muscle_tone": {"mean": 16.3, "sd": 0.4, "person_sd": 0, "trend_per_day": 0, "decimals": 2},
    "muscle_stiffness": {"mean": 294.0, "sd": 8.0, "person_sd": 0, "trend_per_day": 0, "decimals": 1},
}

ANOMALIES = [
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 1, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 2, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 3, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 4, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 5, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 6, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 7, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 8, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 9, "value": 360.0},
    {"astronaut": "a1", "indicator": "peripapillary_trt_left", "day": 10, "value": 360.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 2, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 3, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 4, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 5, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 6, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 7, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 8, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 9, "value": 390.0},
    {"astronaut": "a2", "indicator": "muscle_strength", "day": 10, "value": 390.0},
]
```

| Parameter | Meaning and justification |
| --- | --- |
| `mean`, `sd` | Synthetic observation parameters; the initial force/TRT examples and the added magnitude anchors are documented below. Every noise SD is a chosen software assumption, not an empirical daily astronaut SD. |
| `person_sd = 0` | Disable random offsets between the three fictional astronauts. This is a fixed benchmark design, not a claim that real people have zero between-person variability. Finite sampled baselines will still differ. |
| `trend_per_day = 0` | Hold the synthetic background stationary so injected anomalies can be tested independently. This is a deliberate simulation policy, not missing evidence replaced with a physiological zero. |
| `decimals = 1` | Output precision for this software fixture; not instrument accuracy. |
| `min` / `max` | Grade 0 is deliberately fixed for both eyes; this is a selected scenario, not the full Frisen scale. Repetition counts cannot be negative. These are representation/scenario constraints, not medical normality limits. Other bounds are omitted. |
| 14 preflight days | Software sampling window inherited from the generator. It is not a validated minimum duration for a stable clinical baseline. |
| 10 mission days | Test horizon, not a claim that either disease develops within ten days. A time-stamped injected observation exercises detection; it does not simulate onset or recovery. |
| `SEED = 2027` | Reproducible benchmark with the current generator, indicator order, astronauts a1/a2/a3, and environment. Changing any of these requires revalidation. |
| 360 micrometres | Synthetic left-eye case chosen above the PDF's +55 micrometre review boundary, with margin for the sampled reference. It is not a clinical recommendation or a reported patient observation. |
| 390 N | Synthetic muscle-force case chosen below 80% of the nominal 500 N example. Verify against the sampled personal baseline rather than assuming it is exactly 500 N. |

For this demo only, `muscle_strength` represents right-hand isometric grip force
in N, with the same dynamometer method/posture/summary statistic at every visit.
Do not mix left-hand, knee-extension or whole-body force under this id. This
measurement definition is not a clinical how-to or a replacement for Gonzalo's
instructions. Grip changes alone do not establish whole-body muscle atrophy.
TRT uses the OCT annulus from the Bruch membrane opening to 250 micrometres,
separately for each eye, with the same acquisition/segmentation definition.

The scripted abnormal readings persist to the end of the window; neither case
automatically returns to baseline the next day. The flat plateau is a software
simplification, not a claim of constant disease severity. The first abnormal date
is when the observation becomes available, not a model of onset after launch.

## 3. Time, anomaly and confirmation checks

Use `seed_clock(start, DEMO_DAY)` from the current generator. With this proposed
benchmark's `DEMO_DAY = 1`, the seed starts at 2027-04-01 at 00:00, before the
first observation at 08:00. Another demo day can also work if the seed clock and
anomaly move together; Gonzalo owns that story choice. At reset:

1. Preflight observations are available for computing each personal reference.
   Future mission observations must stay hidden.
2. One advance reveals 42 new observations, including a1's left-eye 360.0
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
by the batch-advance integration tests. They verify attribution to abnormal left
TRT rather than a normal edema grade. These checks do not establish diagnostic performance.

The normal right-eye observation does not raise an alert caused by the left eye.
Attribution requires the new measurement to feed a positive symptom (#91).
The one-open-episode rule also prevents duplicate open episodes.

With the current generator and the exact block above, compute the references from
the generated preflight rows. Expected anchors (rounded here for reporting):

| Case | Sampled personal mean | Sample SD | Injected value | Criterion result |
| --- | ---: | ---: | ---: | --- |
| a1 left TRT | 297.835714 micrometres | 4.183412 micrometres | 360.0 micrometres | Delta +62.164286 micrometres, above the inclusive +55 boundary |
| a2 force | 489.607143 N | 31.203709 N | 390.0 N | 79.6557% of personal reference, below the strict 80% boundary |

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
| Missing values for every catalogue indicator | Supply all fourteen as explicitly synthetic observations with fixed definitions and source-checked magnitudes; do not call chosen noise empirical daily variability. |

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

Generation and lifecycle checks run in isolated temporary storage through
the real generator and core APIs. They cover baseline calculation, newly revealed
automatic batch detection, confirmation, watch protocols and eye independence.
The separate batch-advance regression also checks the exact trigger indicator
and value. These checks do not establish clinical validity or deployed UI timing.

Before treating the final deployed demo as complete: integrate the agreed story
with Gonzalo, have Fran generate the seed, confirm the reference-dependent rules
against the real evaluator, and run the full detection-confirmation-protocol path.
This document does not change the generator, runtime files, seed or medical rules.
An evidence/documentation PR can be reviewed without activating the benchmark.
Edu accepts design A and all fourteen indicators. The complete block can be
handed to Fran without changing the generator API. The final story and app/README
synthetic labels still require owner integration (#34/#35/#78). Scientific
plausibility does not establish population validity or diagnostic accuracy.

### Human plausibility of the selected magnitudes

[Dodds et al., PLOS ONE 2014, Table 2](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0113637)
reports a 51 kg grip median and 38-64 kg 10th-90th centiles for men aged 30.
These dynamometer readings are force-equivalent (kgf); conversion uses
1 kgf = 9.80665 N. The proposed 500 N is about 51.0 kgf, and the complete
generated force set (390.0-546.2 N) is about 39.8-55.7 kgf. This supports physical
plausibility for selected fictional adult grip profiles, not a universal normal
range, an astronaut norm, or suitability for all ages/sexes. No demographic
inference about the fictional astronauts is made from this example comparison.

The generated TRT values are checked against the 272-420
micrometre preflight range reported for the selected annulus in Patel Table 2.
This is an observed-cohort envelope used as a plausibility check, not a clinical
reference interval: within it, an individual's change can still be concerning.
The 5 micrometre and 25 N noise SDs remain deliberate synthetic choices, not
empirical daily SDs; their small scales do not establish validated repeatability.
Zero trend and person offsets describe the controlled fixture, not human biology.

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
mission days or scenario requires revalidation. Passing controls establish data
reproducibility and automatic detection-confirmation-protocol flows.
Population validity and the final demo story remain separate acceptance items.


## 8. Fourteen-indicator measurement definitions and magnitude anchors

All added SDs below are explicitly chosen synthetic observation noise. None is
copied from a population SD, SEM or confidence interval. Person offsets and
trends are deliberately zero for this controlled demo. The fictional records
are not drawn from a joint physiological population model. The programme does
not instruct real people to perform these tests daily; some cited tests require
longer recovery and specialised facilities.

| Indicator(s) | Fixed definition for this dataset | Synthetic mean / noise SD | Magnitude rationale |
| --- | --- | --- | --- |
| muscle_strength | Right-hand isometric grip, same dynamometer/posture/summary | 500 / 25 N | Previously documented adult grip comparison; not a leg-force measure. |
| muscle_area | Right lumbar multifidus at L5, same ultrasound cross-section | 10 / 0.2 cm2 | Hides Table 1 reports L5 average about 10 cm2; used only for scale. It does not supply an empirical right-side mean or daily SD. Our generated right-side references never pool sides. |
| muscle_power | Right-knee concentric extension peak mechanical power at 60 degrees/s | 186 / 8 W | Laughlin Table II reports peak torque 177.6 N m; P = torque times angular speed gives about 186 W at pi/3 rad/s. This is a same-speed derived scale, not a reported daily power series. |
| muscle_endurance | Right-knee extension repetitions with load fixed at 40% of preflight 1RM, fixed task/tempo | 14.4 / 1 repetitions, rounded to integers | Hillen Results 3.1 reports about 14 repetitions at 40% 1RM. The population spread/error statistics are not our chosen daily noise. The absolute load stays fixed during the simulated mission. |
| muscle_tone | Right rectus femoris at rest, fixed MyotonPRO site/posture | 16.3 / 0.4 Hz | Lukas Table 9 healthy-control dominant-side mean 16.28 Hz supports this scale; no daily variance or right-side population norm is inferred. |
| muscle_stiffness | Same right rectus femoris site/method as tone | 294 / 8 N/m | Lukas Table 9 healthy-control dominant-side mean 294 N/m supports this scale; not a stand-alone atrophy diagnosis. |
| peripapillary_trt_left/right | OCT BMO-to-250-micrometre annulus, separate eye references | 300 / 5 micrometres each | Existing synthetic anchor and Patel observed-scale comparison. |
| optic_disc_edema_grade_left/right | Expert Fris?n grade, each eye separately | 0 / 0 grade each, fixed 0 | Selected Fris?n grade 0 appearance; this does not establish absence of edema. Brunstetter 2024 reported grade 0 despite objective edema and substantial TRT change. No Gaussian grade noise or invented positive SD is added. |
| refraction_left/right | Cycloplegic spherical-equivalent refraction in D, same instrument/method per eye | -1 / 0.05 D each | Brunstetter's preflight -1 D establishes a plausible mild-myopic magnitude, not a population distribution. Continuous output represents a numeric refraction estimate, not a spectacle prescription rounded to lens steps. |
| visual_acuity_left/right | Corrected monocular computer-estimated logMAR threshold, fixed FrACT-style task/settings | 0 / 0.03 logMAR each | 0 corresponds to 20/20; a continuous threshold estimate permits hundredths and negative values (better acuity). Bach supports the method/output scale; our chosen noise is not its published limits of agreement. |

Sources checked for these definitions:

- [Hides et al., Spine Journal 2021, Table 1, p. 483](https://australian.physio/sites/default/files/RESEARCH%26PUBLICATIONS/PRF/PRF%3A%20Image%20library/2021_Hides%20Astronaut%20paper_The%20Spine%20Journal-main-min.pdf).
- [Laughlin et al., NASA ISS isokinetic reliability, Methods/Table I/Table II](https://ntrs.nasa.gov/api/citations/20090019649/downloads/20090019649.pdf). Peak torque is not force in N; only the explicit same-speed power conversion is used here.
- [Hillen et al., Muscles 2026, Methods/Results 3.1](https://www.mdpi.com/2813-0413/5/2/26). Right-leg testing and load/tempo are fixed; recovery procedures in that study are not replaced with the app's estimated confirmation timer.
- [Lukas et al., Journal of Neurology 2023, Table 9](https://pmc.ncbi.nlm.nih.gov/articles/PMC10576663/). Dominant-side group values are magnitude anchors; side-specific daily distributions are not available.
- [Bach, FrACT study, Methods/Results](https://pmc.ncbi.nlm.nih.gov/articles/PMC11868300/). This supports computer-estimated logMAR rather than an invented letter-count scale; no equivalence to uncorrected or binocular acuity is assumed.

Representation checks: edema grades are integers fixed to zero and are evaluated
by raw rules, so a zero-SD grade baseline is intentionally not usable for z-scores.
All continuous baseline-dependent indicators retain positive sample SD. Endurance
counts are non-negative integers. Negative refraction and negative logMAR are
valid and must not be clipped to zero. No cross-indicator covariance is fitted;
these independent synthetic channels cannot validate a causal muscle/eye model.

With the exact fixed seed, expansion to fourteen consumes different random draws
for subsequent astronauts. Recompute every personal reference: the original
three-indicator reference for a2 is obsolete. At the second advance, the background
also opens a watch for a3 and queues a muscle finding for a1, whose SANS episode
stays open. These are statistical review events, not extra scripted disease cases.
Do not hide them or claim an empirical false-alert rate from this fixture.

The final demo story remains Gonzalo's responsibility. The selected anomaly
values and persistence are unchanged; all fourteen parameter entries are now
present. Fran's integrated generator still supplies the earlier three-indicator
block; expanding it and regenerating the seed remains owner integration work. The initial dataset has
1008 rows (3 astronauts times 14 indicators times 24 observation dates).


## 9. Accepted synthetic scope and biological interpretation

Edu explicitly authorizes synthetic observations for this handoff, subject to
biological plausibility (2026-11-14). Section 2 is the complete fourteen-indicator
delivery; the earlier three-indicator block records the currently integrated
version only. No new clinical threshold, advice or repeat interval is introduced.

Interpret the ten dates as an observation window during an unspecified stage of
an ongoing mission. Day 1 means the first observation revealed by this software
scenario, not the first day after launch. Preflight rows are frozen reference
observations; their compact storage dates do not model the elapsed time between
preflight assessment, launch and the observation window. No launch date or onset
duration is supplied by this dataset. The abrupt change between reference and
first observed abnormal value is an unobserved interval, not a one-day biological
transition. The last generated day is not a recovery endpoint.

The scripted TRT and grip findings persist through the remaining window. Exact
repetition of 360 micrometres or 390 N is a deterministic software control, not a
claim of zero instrument noise or a literal patient time series. Stationary
background channels and independent noise are simplifying assumptions; they do
not imply that strength, area, power and endurance must change together across
different muscles, or that every ocular finding must coexist. Grade 0 must not
be narrated as proof of absent edema. A normal right-eye channel must not inherit
a left-eye alert or reference.

The source comparisons in sections 7-8 support the selected numerical scales,
not a joint physiological model. The grip comparison describes selected adult
profiles and is not a sex-, age- or task-independent astronaut normal range.
The generator's noise SDs are explicitly synthetic. Do not infer diagnostic
accuracy, disease prevalence or a false-alert rate from these fixed records.

Integration acceptance: Fran copies section 2 without changing units, indicator
order, measurement definitions or persistence, regenerates both seed and script
data, and runs the existing generator checks plus this handoff suite. Public
wording remains: "Synthetic demonstration data. These fictional measurements
demonstrate the software workflow; they are not astronaut reference values or
a validated model of physiology or disease progression." Ansel reviews/merges;
Gonzalo owns presentation timing. The configured estimated confirmation delays
remain a separate scientific-source task (#43).
