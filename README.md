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

1. Click **Astronaut A**, then **International Space Station**. In Main Menu → *Demo controls*, press **Reset demo**. You will explore fictional, synthetic measurements.
2. Press **Advance mission 24 h** to reveal an ocular measurement alert. Open **Check-in** to compare it with your personal pre-flight baseline.
3. Use **Simulate wait** and repeat the flagged measurement with the demo value (**360** µm) to confirm the anomaly.
4. Open **Protocols** and follow the guidance through to medical follow-up. SpaceDoc guides you; it does not diagnose.

## Meet the mascot

**Lumi**, a glowing LED alien head drawn in code (SVG, no images). Its colour and shape show the astronaut's state at a glance: blue when everything is nominal, amber while a symptom or an alert is being followed up, red for an urgent alarm. It narrates every astronaut screen so the app can be followed at a glance, even mid-task:

- **On the Welcome** it is big and centred; on the other screens it is a compact assistant line above the cards and buttons.
- **Next to a chart or a protocol flowchart** it slides to the left and shrinks, so the visual takes the right side.
- **Subtitles** appear word by word while its LED mouth talks; with **Voice** on (top-right toggle) it reads them aloud with the browser's own speech synthesis, in sync. It only speaks a new line, never the same one twice.
- It never invents health content: it reads the alert, question or protocol step the screen would otherwise show.

It is not shown on Trends or Tutorials, where the charts and the practice flowchart need the space. Its name is still to be chosen by the team.

## How it works

Measurement → **personal baseline** (pre-flight mean and spread of each astronaut) → **symptom levels** (watch / concern) from rules written by our health lead with their sources → **problem state** → **confirmation** with a repeat measurement → **protocol** (a flowchart with steps, questions, measurements and contacts with the crew medical officer or flight surgeons). Simulated mission time drives the demo: advancing it reveals new synthetic measurements and drains the progress bars.
Architecture and contracts: see [`AGENTS.md`](AGENTS.md).

## Health indicators and problems

Two problems are covered: [SANS (NASA HRP)](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/) and [reduced muscle size, strength and endurance (NASA HRP)](https://www.nasa.gov/directorates/esdmd/hhp/muscle-risk/). The nine check-ins contain fourteen indicators; each eye/site keeps its own personal baseline.

| Problem | Check-in | Indicators and units | Public method reference |
| --- | --- | --- | --- |
| SANS | Eye scan (OCT) | Left/right peripapillary total retinal thickness (µm), BMO-to-250-µm annulus | [Patel et al., 2018](https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2667551) |
| SANS | Optic disc check | Left/right clinician-assessed Frisén grade | [Brunstetter et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11273286/) |
| SANS | Refraction | Left/right cycloplegic spherical-equivalent refraction (D) | [Brunstetter et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11273286/); [scalar definition](https://pmc.ncbi.nlm.nih.gov/articles/PMC3930272/) |
| SANS | Visual acuity | Left/right corrected monocular acuity (logMAR) | [Bach/FrACT](https://pmc.ncbi.nlm.nih.gov/articles/PMC11868300/); [MedlinePlus](https://medlineplus.gov/ency/article/003396.htm) |
| Muscle | Muscle strength | Right-hand grip force (N), not knee strength | [PhenX/NHANES protocol](https://www.phenxtoolkit.org/protocols/view/150302) |
| Muscle | Muscle size | Right L5 multifidus cross-sectional area (cm²) | [Hides et al., 2021](https://australian.physio/sites/default/files/RESEARCH%26PUBLICATIONS/PRF/PRF%3A%20Image%20library/2021_Hides%20Astronaut%20paper_The%20Spine%20Journal-main-min.pdf) |
| Muscle | Muscle power | Right-knee isokinetic mechanical power (W); project derivation from torque × angular speed | [Laughlin et al., NASA ISS reliability](https://ntrs.nasa.gov/api/citations/20090019649/downloads/20090019649.pdf) |
| Muscle | Muscle endurance | Right-knee repetitions at a fixed preflight load and tempo | [Hillen et al., 2026](https://www.mdpi.com/2813-0413/5/2/26) |
| Muscle | Muscle tone and stiffness | Right rectus femoris: frequency (Hz) and stiffness (N/m) | [MyotonPRO guide](https://myoton.com/wp-content/uploads/2025/01/Quick-Guide-A4.pdf); [ESA Myotones](https://www.esa.int/ESA_Multimedia/Images/2018/07/Tricorder) |

Method references do not validate every alert threshold. NASA's muscle-strength retention requirement and published SANS criteria are distinguished from the team's experimental statistical bands, triage choices and estimated confirmation waits in [`config/`](config/). Criteria are version-specific; source/access limitations are recorded in the [medical source review](docs/MEDICAL_SOURCE_REVIEW.md). Numerical concern requests priority review, not an automatic diagnosis or medical urgency. Activity-bar timers are [synthetic, non-clinical demo choices](docs/CHECK_IN_INTERVALS.md).

## NASA data and resources used

The demo uses locally generated fictional observations, not downloaded astronaut patient records. NASA material informs requirements, monitoring context and prototype guidance:

- [NASA-STD-3001 Vol. 1, Rev. C](https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_1), [Human Performance §4.6.2](https://www.nasa.gov/reference/4-0-human-performance/): muscle-strength retention requirement; not a universal injury threshold.
- [SANS 2023 Clinical Update](https://ntrs.nasa.gov/citations/20220014606): early/concerning structural findings and functional-impact criteria; [OCHMO-MTB-001](https://www.nasa.gov/wp-content/uploads/2024/02/ochmo-mtb-001-sans.pdf): examinations, monitoring and treatment-evidence limits.
- [SANS evidence report, 2017/2018](https://ntrs.nasa.gov/api/citations/20180000936/downloads/20180000936.pdf), [HRP SANS evidence report](https://humanresearchroadmap.nasa.gov/Evidence/reports/SANS.pdf), and [muscle evidence record](https://ntrs.nasa.gov/citations/20100039152): background for structural/functional monitoring and symptom guidance.
- [Exercise Overview](https://www.nasa.gov/ochmo-tb-031-exercise-overview-2/), [Astronaut Exercise](https://www.nasa.gov/missions/station/iss-research/astronaut-exercise/), and [nutrition monographs](https://www.nasa.gov/wp-content/uploads/2024/10/human-adaptation-to-spaceflight-the-role-of-nutrition.pdf) ([2021 edition](https://www.nasa.gov/wp-content/uploads/2024/08/human-adaptation-2021-final-b.pdf)): supervised exercise, recovery and nutrition context; no autonomous prescriptions.
- [Isokinetic reliability study](https://ntrs.nasa.gov/api/citations/20090019649/downloads/20090019649.pdf): task/method evidence; its torque and total-work outcomes are not interchangeable with force, power or repetition counts.
- [Astronaut health care](https://www.nasa.gov/missions/station/faq-the-real-story-about-astronaut-health-care-in-space/), [Distance From Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/), and [Mars communication delay/disruption](https://www.nasa.gov/wp-content/uploads/2024/01/mars-communications-disruption-and-delay.pdf): local care, remote support and communication limits.
- Environment references: [ISS microgravity](https://www.nasa.gov/wp-content/uploads/2023/03/np-2015-03-018-jsc-cellular-biology-iss-mini-book-508.pdf), [ISS communications](https://www.nasa.gov/missions/station/the-space-network-cell-towers-for-astronauts/), [Moon gravity](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/moon/), [Mars facts](https://www.jpl.nasa.gov/news/press_kits/insight/landing/facts/mars-at-a-glance/), and [Mars signal travel](https://science.nasa.gov/blog/speaking-percys-language-how-to-talk-so-perseverance-will-listen/). Gravity does not scale medical thresholds; signal travel does not guarantee a clinical reply.
- Research context: [partial-gravity review](https://ntrs.nasa.gov/citations/20210019591), [Thigh Cuff](https://www.nasa.gov/reference/thigh-cuff/), [HRP 2026 research plans](https://www.nasa.gov/wp-content/uploads/2026/08/hrp-rap-for-web-62026-hhc.pdf), and [Why Moon and Mars](https://ntrs.nasa.gov/api/citations/20250009282/downloads/2025%20IAC%20-%20Why%20Moon%20and%20Mars%20-%200916%20Edits.pdf): background/research, not approved treatment instructions.

## Other data and references

The following references support methods, context or research comparisons; they are not imported clinical datasets. The [synthetic-data handoff](docs/DEMO_DATA_HANDOFF.md) distinguishes integrated inputs, proposed inputs and empirical alternatives. The team's supplied guides are independently authored prototype material, not NASA publications; their public references and access limitations are catalogued in the [25-source extraction](docs/MEDICAL_SOURCE_REVIEW.md). [Protocol diagrams](docs/PROTOCOL_FLOWCHARTS.md) map that evidence to guidance; [subjective-issue provenance](docs/sintomas_subjetivos_atrofia_SANS.md) distinguishes symptoms from alarms.

- [Patel et al., 2018](https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2667551): OCT region and observed cohort magnitudes, not personal daily SDs.
- [Brunstetter et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11273286/): eye-specific case observations; grade 0 does not exclude OCT changes.
- [Gew et al., 2026 consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC13462731/): guide-selected refractive criterion profile; full-text verification limits are explicit in the source review.
- [Pardon et al., 2022](https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2797831): alternative OCT cohort context; standard error is not daily SD.
- [Macias et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7118682/): time/region-specific ocular research, not a synthetic disease trajectory.
- [Kita et al., 2015](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144721): alternative OCT repeatability method, not proof of equivalence to the configured region/device.
- [OCT repeatability study](https://doi.org/10.1371/journal.pone.0221466): acquisition-duration analogy for an explicitly estimated prototype timer, not a prescribed SANS wait.
- [Hides et al., 2021](https://australian.physio/sites/default/files/RESEARCH%26PUBLICATIONS/PRF/PRF%3A%20Image%20library/2021_Hides%20Astronaut%20paper_The%20Spine%20Journal-main-min.pdf): multifidus ultrasound acquisition and research magnitude context.
- [Scott et al., 2021, Tele-SUS](https://pmc.ncbi.nlm.nih.gov/articles/PMC8047175/): teleguided muscle-ultrasound research, not autonomous acquisition validation.
- [Hillen et al., 2026](https://www.mdpi.com/2813-0413/5/2/26): repetition-endurance task and reliability.
- [Lukas et al., 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10576663/): terrestrial myotonometry magnitude comparisons, not astronaut daily variation.
- [MyotonPRO Quick Guide](https://myoton.com/wp-content/uploads/2025/01/Quick-Guide-A4.pdf): marked-site acquisition and separate frequency/stiffness outputs.
- [PhenX/NHANES grip protocol](https://www.phenxtoolkit.org/protocols/view/150302): standardized dynamometer setup.
- [Dodds et al., 2014](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0113637): adult grip magnitude comparison, not universal astronaut norms.
- [Aben et al., 2020](https://www.mdpi.com/2075-4663/8/5/73): alternative force-task evidence, not the configured grip task.
- [CDC/NIOSH strength assessment](https://stacks.cdc.gov/view/cdc/9182/cdc_9182_DS1.pdf): rest-period analogy for a prototype timer; no universal post-anomaly recovery claim.
- [Bach/FrACT](https://pmc.ncbi.nlm.nih.gov/articles/PMC11868300/): computer-estimated logMAR method.
- [Refraction scalar definition](https://pmc.ncbi.nlm.nih.gov/articles/PMC3930272/): spherical equivalent is distinct from an unqualified sphere reading.
- [MedlinePlus visual-acuity test](https://medlineplus.gov/ency/article/003396.htm): monocular assessment and correction.
- [ESA Tricorder/Myotones](https://www.esa.int/ESA_Multimedia/Images/2018/07/Tricorder): tone/stiffness research context.
- [DLR-NASA functional performance study](https://www.dlr.de/en/blog/archive/2025/dlr-nasa-bed-rest-study-functional-performance-test): task performance and unloading context.
- [Canadian Space Agency reconditioning](https://www.asc-csa.gc.ca/eng/youth-educators/activities/fitness-and-nutrition/return-and-reconditioning.asp): educational postflight-rehabilitation context.
- [ESA bedrest](https://explorationscience.esa.int/platforms/bedrest/): terrestrial analogue background.
- [ESA Extended space dive](https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/Extended_space_dive): dry-immersion research background.
- [ESA Nebula communications project](https://nebula.esa.int/4000136202): latency context; access limitation recorded in the source review.
- [ESA Moon calling Earth](https://www.esa.int/media/ten-things-you-didn-t-know-about-the-moon-moon-calling-earth): lunar light-time reference.
- [American Heart Association pulse measurement](https://www.heart.org/en/health-topics/high-blood-pressure/the-facts-about-high-blood-pressure/all-about-heart-rate-pulse): retained legacy-catalogue measurement guidance.
- [American Heart Association cuff technique](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/monitoring-your-blood-pressure-at-home): retained legacy blood-pressure acquisition guidance.
- [American Heart Association blood-pressure terms](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings): retained legacy blood-pressure definitions.
- [CDC glucose monitoring](https://www.cdc.gov/diabetes/diabetes-testing/monitoring-blood-sugar.html): retained legacy-catalogue guidance.
- [MedlinePlus temperature measurement](https://medlineplus.gov/ency/article/003400.htm): retained legacy-catalogue guidance.
- [NHLBI sleep diary](https://www.nhlbi.nih.gov/resources/sleep-diary): retained legacy-catalogue recording convention.

Legacy catalogue entries are not additional supported problems or real check-in cards. The mascot is rendered from in-repository SVG/CSS/JS with browser speech synthesis; application dependencies are declared in [`requirements.txt`](requirements.txt).

## AI usage

AI-generated code is marked with an `AI-assisted` header comment in each file. Which AI tools each team member used, and for what:

- **Edu (science and health):** Codex assisted with source searches and PDF reference extraction, medical configuration and protocol drafts, synthetic demo specifications, tests, flowcharts and documentation; Edu personally reviewed the generated medical configuration, protocol text, source summaries and related tests. This work does not constitute clinical validation.
- **Ansel (architecture, integration and mascot):** Claude Code for the architecture and contracts, code review and merges, integration of the pages, the mission-console look, the mascot Lumi (face, subtitles, voice) and its tests and documentation; Lumi's face was designed by Ansel with Claude. Ansel reviewed and ran every change before merging.
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
