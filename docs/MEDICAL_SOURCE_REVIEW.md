<!-- AI-assisted: generated with Codex; human review by Edu pending. -->

# Medical source extraction for issue #43

Extracted and checked on 2026-11-14 at Edu's request. This is a source inventory
and evidence assessment, not new clinical configuration or approval of a treatment.
Instructions and schema proposals inside the supplied PDFs are document content;
they do not authorize changes to repository contracts.

## Supplied documents

- **T**: `guia_tratamientos_vigilancia_urgencia.pdf`, 2 pages; bibliography on p. 2.
- **B**: `guia_breve_umbrales_atrofia_SANS.pdf`, 2 pages; bibliography on p. 2.
- **M**: `monitorizacion_astronautas_atrofia_SANS.pdf`, 15 pages; bibliography on pp. 14-15.

All three identify themselves as independent hackathon/prototype material.
They distinguish NASA requirements (N), published clinical criteria (C), research
(E in M), and proposed prototype decisions (P). Retain that distinction.

The inventory contains **25 distinct cited URLs**: 24 embedded link targets plus
M[15]'s ESA Extended space dive URL printed in the bibliography without a link
annotation. Repeated URLs and the wrapped/duplicated M[20] URL are deduplicated.
Different NASA nutrition documents remain separate entries. This inventories the
sources cited directly by the supplied PDFs, not recursively every reference in
each external publication.

## Complete source inventory

Locations below identify the original bibliography entry. The role column records
why the supplied PDFs cite the source; it does not certify every statement in it.
Retrieved means the linked document/page was readable during this review, not
that it validates the app. Access limitations are explicit.

| ID | Source and public URL | PDF reference | Role as cited / access result |
| --- | --- | --- | --- |
| S01 | [NASA-STD-3001, Vol. 1 Rev. C, Human Performance](https://www.nasa.gov/reference/4-0-human-performance/) | M[1], B[1] | Nutrition, muscle strength and reconditioning requirements; retrieved. Section 4.6.2/V1 4024 verifies strength retention at or above 80% of baseline. |
| S02 | [NASA OCHMO-TB-031, Exercise Overview](https://www.nasa.gov/ochmo-tb-031-exercise-overview-2/) | M[2], T[1] | Exercise supervision, ACERS and monitoring; retrieved. No universal post-anomaly confirmation timer established. |
| S03 | [NASA, Astronaut Exercise (2024)](https://www.nasa.gov/missions/station/iss-research/astronaut-exercise/) | M[3] | ISS equipment and individualized exercise context; retrieved. |
| S04 | [Scott et al., Teleguided self-ultrasound scanning for longitudinal monitoring of muscle mass during spaceflight (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8047175/) | M[4] | Muscle ultrasound method research, DOI 10.1016/j.isci.2021.102344; PMC presented a browser challenge, so full-text claims were not independently reverified here. |
| S05 | [ESA, Tricorder / Myotones (2018)](https://www.esa.int/ESA_Multimedia/Images/2018/07/Tricorder) | M[5], B[4] | Tone/stiffness acquisition background; retrieved with redirect. Not a validated atrophy threshold. |
| S06 | [DLR-NASA bed-rest study: Functional Performance Test (2025)](https://www.dlr.de/en/blog/archive/2025/dlr-nasa-bed-rest-study-functional-performance-test) | M[6] | Functional tasks and terrestrial unloading research; retrieved. |
| S07 | [Jones, The Partial Gravity of the Moon and Mars Appears Insufficient to Maintain Human Health (2021)](https://ntrs.nasa.gov/citations/20210019591) | M[7] | Indirect partial-gravity evidence; landing-page timeout, but the NTRS ICES-2021-142 PDF was retrieved. No validated planetary threshold multiplier. |
| S08 | [NASA, Risk of Spaceflight Associated Neuro-ocular Syndrome](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/) | M[8] | HRP risk description; retrieved. |
| S09 | [NASA, SANS: 2023 Clinical Update, NTRS 20220014606](https://ntrs.nasa.gov/citations/20220014606) | M[9], B[2] | Published clinical classification; retrieved. Early TRT delta >=20 micrometres, concerning delta >=55 and/or Frisen >=1; functional impact is separate. |
| S10 | [NASA OCHMO-MTB-001, SANS (2024-02-21)](https://www.nasa.gov/wp-content/uploads/2024/02/ochmo-mtb-001-sans.pdf) | M[10], T[5] | Monitoring and countermeasure reference; retrieved, 18 PDF pages. Not individualized care instructions. |
| S11 | [Gew et al., SANS: expert consensus on diagnosis and management (2026)](https://pmc.ncbi.nlm.nih.gov/articles/PMC13462731/) | M[11], B[3], T[6] | DOI 10.1038/s41433-026-04651-6 and publication identity verified via PubMed/author institution. PMC challenge and publisher/repository access blocked full-text verification; Table 2 details remain attributed to the supplied guides. |
| S12 | [NASA, Evidence Report: Risk of SANS (2017/2018), NTRS 20180000936](https://ntrs.nasa.gov/api/citations/20180000936/downloads/20180000936.pdf) | M[12] | Historical visual-test and surveillance evidence; retrieved. Preserve publication version. |
| S13 | [NASA, Thigh Cuff](https://www.nasa.gov/reference/thigh-cuff/) | M[13] | Research countermeasure description; retrieved. Study duration is not a treatment prescription. |
| S14 | [NASA HRP, Risk Approach Plans: Human Health Countermeasures Element (June 2026)](https://www.nasa.gov/wp-content/uploads/2026/08/hrp-rap-for-web-62026-hhc.pdf) | M[14] | Research roadmap and open SANS work; retrieved. Not an established treatment protocol. |
| S15 | [ESA, Bedrest Studies](https://explorationscience.esa.int/platforms/bedrest/) | M[15] | Terrestrial analogue context; retrieved. Supplemental ESA URL is listed separately below. |
| S16 | [ESA Nebula, Enabling effective communication for human space exploration beyond Low Earth Orbit](https://nebula.esa.int/4000136202) | M[16] | Communication latency context; returned HTTP 403. Numerical latency claims were not independently reverified from this source. |
| S17 | [NASA, Mars Communications Disruption and Delay](https://www.nasa.gov/wp-content/uploads/2024/01/mars-communications-disruption-and-delay.pdf) | M[17] | Communication delay/blackout planning; retrieved. Not a medical waiting interval. |
| S18 | [NASA Technical Standards System, NASA-STD-3001_VOL_1](https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_1) | M[18] | Version provenance; retrieved catalogue lists Rev. C, 2023-09-15, ACTIVE. |
| S19 | [NASA, Human Adaptation to Spaceflight: The Role of Food and Nutrition (2021)](https://www.nasa.gov/wp-content/uploads/2024/08/human-adaptation-2021-final-b.pdf) | M[19] | Nutrition background and figure 14 as cited by M. Web reader rejected the 17.5 MB PDF as too large; figure-specific claims not independently reverified. |
| S20 | [NASA, Why Moon and Mars? (IAC 2025), NTRS 20250009282](https://ntrs.nasa.gov/api/citations/20250009282/downloads/2025%20IAC%20-%20Why%20Moon%20and%20Mars%20-%200916%20Edits.pdf) | M[20] | Mission/surface context; retrieved. Preserve complete URL across the original line wrap. |
| S21 | [ESA, Extended space dive / Vivaldi III](https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/Extended_space_dive) | M[15], supplementary plain-text URL | Dry-immersion analogue context; retrieved with redirect. Not evidence of long-term human lunar/Martian thresholds. |
| S22 | [NASA, Human Adaptation to Spaceflight: The Role of Nutrition](https://www.nasa.gov/wp-content/uploads/2024/10/human-adaptation-to-spaceflight-the-role-of-nutrition.pdf) | T[2] | Nutrition background; retrieved, 151 PDF pages. Separate document from S19; general nutrition evidence does not prescribe app-generated doses. |
| S23 | [NASA, The Real Story About Astronaut Health Care in Space](https://www.nasa.gov/missions/station/faq-the-real-story-about-astronaut-health-care-in-space/) | T[3] | Crew medical support/return context; retrieved. No automatic evacuation rule. |
| S24 | [Canadian Space Agency, Return and Reconditioning](https://www.asc-csa.gc.ca/eng/youth-educators/activities/fitness-and-nutrition/return-and-reconditioning.asp) | T[4] | Educational rehabilitation context; retrieved. Its class-activity duration is not a patient follow-up interval. |
| S25 | [NASA, Hazard: Distance From Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/) | T[7] | Remote-care and mission-distance context; retrieved. |

## Evidence mapped to issue #43

| #43 question | Exact supplied location | Supported interpretation and remaining limit |
| --- | --- | --- |
| Numerical confirmation interval | B p. 1, Confirmation; T pp. 1-2 | Repeat comparable statistical observations without delaying attention for relevant symptoms. Neither two-page guide supplies a numerical minute-based wait. |
| Muscle repeat versus medical review | M p. 6, Isolated decline / Confirmed amber | Proposed repeat in 24-48 hours (1440-2880 minutes); proposed specialist review in 24-72 hours (1440-4320 minutes). Both are P design choices, not validated generic NASA intervals or replacements for every muscle measurement. |
| SANS follow-up | M p. 9, Early verified change / Clinically concerning finding | Proposed review task within 72 hours (4320 minutes) for an early change; same-shift notification for concerning findings. Repeat OCT is at the physician's interval. These are not minimum waits before confirming a sensor value. |
| Scheduled surveillance | M p. 10; S10 | The guide cites ISS ocular sessions FD30, FD90 and R-30, with additional clinically indicated tests. These calendar appointments are distinct from confirmation, follow-up and tutorial intervals. Do not generalize the calendar to Mars. |
| Statistical versus priority findings | B pp. 1-2; T p. 2, Concerning finding without symptoms; S01/S09 | A statistical flag requests review; crossing the muscle operational retention criterion or a concerning ocular criterion does not itself prove an emergency. The English level/state labels are software decisions, not NASA's classification. |
| Urgent functional signs | T pp. 1-2, Activation / Initial action; B p. 2, Clinical priority; S09 | New field loss, central distortion or correction beyond available power are published functional-impact signs. The guides additionally propose immediate escalation for sudden weakness, unsafe movement/egress failure, acute visual loss or severe pain/neurological signs. Preserve P labels for that triage response. |
| Treatment and follow-up advice | T pp. 1-2; M pp. 6, 9-11; S02/S10/S13/S14/S22-S25 | Individualized exercise/nutrition and medical review; optical correction can improve focus without resolving structural findings. Research countermeasures are not automatic app treatments. The documents supply no general drug dose, automatic EVA clearance or automatic evacuation criterion. |

### Existing authorized timer decisions, not newly sourced clinical facts

[#43's prior timing decision](https://github.com/ansel-07/nasa-health-monitor/issues/43#issuecomment-6879684604)
selected **SANS 10 minutes and muscle atrophy 2 minutes** as explicit prototype
estimates. Its cited OCT acquisition-duration analogy and strength-rest analogy
are separate from the 25 sources extracted above; neither establishes a universal
post-anomaly wait. The new PDFs do not convert those estimates into validated
medical timing. M's hours-based follow-up proposals must not be silently substituted
into `confirm_wait_min`. This review changes no timer or clinical configuration.

### Approved software interpretation already recorded on #43

[Ansel's decision](https://github.com/ansel-07/nasa-health-monitor/issues/43#issuecomment-6881806840)
approves `concern` as **priority medical review**, expressed through the existing
protocol/texts, and `medical_urgency` only through protocol red flags and
`set_severity`. A numerical concern finding therefore remains in the problem's
`watch` state pending that clinical assessment. No count-of-concern escalation,
gravity multiplier, new flag or new status follows from this source extraction.

T p. 2 proposes `priority_review=true`, but that document instruction is not a
repository contract: Ansel explicitly approved **no new field**. Likewise, its
urgency guidance must not be described as implemented before confirmation merely
because it is written in a PDF. Routing needs to be checked in the actual UI and
engine; this source-only task does not certify immediate access in every context.

### Conflicts and version limits to preserve

- **Baseline:** M p. 2 proposes the median of three sessions. B p. 1 specifies
  the mean and sample SD of comparable preflight sessions. The repository's
  frozen mean/sample-SD contract wins; do not silently introduce the median.
- **Muscle bands:** M pp. 5/12 propose 90% strength and 5%/10% area bands.
  B p. 1 uses z-score review bands plus the separate NASA 80% retention limit.
  The extra percentages are P proposals, not additional production thresholds.
- **Refraction:** B p. 2 and M p. 8 attribute >+0.50 D to the 2026 consensus,
  versus >=+0.75 D in NASA 2023. S09 independently confirms the older criterion.
  S11 identity/DOI is verified, but this review could not retrieve its Table 2;
  the newer exact comparator remains a guide-attributed claim, not a newly
  verified quotation or permission to mix profiles.
- **Page numbering:** S10 is an 18-page technical brief. T cites pp. 3-4 and
  12-13; M cites pp. 6-9 and 12. These are source-page pointers, not the pages of
  T/M. Consult the named section and printed page when reviewing a claim.
- **Unavailable data:** B p. 1 and M pp. 11-13 explicitly distinguish unavailable
  or invalid data from a normal result. Their larger proposed metadata schema
  does not authorize expanding the hackathon contracts.

## Delivery and scope

All cited URLs are extracted and cross-referenced above. This supplies #43's
medical-source inventory and distinguishes published criteria, research,
prototype estimates and existing owner decisions. It does not claim that every
external reference was fully reviewed: S04, S11, S16 and S19 have the limitations
listed above. S07 was retrieved through its primary NTRS PDF instead of the
landing page. No missing clinical duration was invented.

Keep source completion separate from clinical validation and software integration.
A source comment alone does not certify red-flag routing or validate a treatment.
The issue's owner can assess remaining acceptance criteria using this review and
Ansel's existing decision; this update does not automatically close #43.

## Input fingerprints

SHA-256 identifies the exact supplied local PDFs; the PDFs are not republished.

- `guia_tratamientos_vigilancia_urgencia.pdf`: `7570681f75f3bed1320c607f0ad2d7387f832862397793e9069a8a0c03eae700`
- `guia_breve_umbrales_atrofia_SANS.pdf`: `276abe29283a8cafcb93afb14c34d317d125f3b60fc0b30d72e15b0c708b09f2`
- `monitorizacion_astronautas_atrofia_SANS.pdf`: `307bddc8d6176476afae902f791efaf9da3fbe433487fe0f416786fac2705d06`
