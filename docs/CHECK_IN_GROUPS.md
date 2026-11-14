<!-- AI-assisted: generated with Codex; human review by Edu pending. -->

# Check-in grouping review (#98)

Reviewed on 2026-11-14 against the measurement definitions in
`config/indicators.json`. Group by acquisition method, not by the health problem
being monitored. These are project workflow decisions; the cited publications
describe methods, not an officially approved nine-card application layout.

| Check-in ID | Indicators | Grouping rationale |
| --- | --- | --- |
| `eye_oct` | `peripapillary_trt_left`, `peripapillary_trt_right` | Same OCT acquisition/analysis method for each eye; retain separate values and preflight references. |
| `optic_disc` | `optic_disc_edema_grade_left`, `optic_disc_edema_grade_right` | Clinician grading of optic-disc images for each eye; not an OCT-derived grade. |
| `refraction` | `refraction_left`, `refraction_right` | Same clinician refraction method, with a separate signed spherical-equivalent result per eye. |
| `visual_acuity` | `visual_acuity_left`, `visual_acuity_right` | Same corrected monocular test, performed separately for each eye. |
| `muscle_strength_test` | `muscle_strength` | Right-hand grip dynamometry; distinct from knee power or endurance. |
| `muscle_size` | `muscle_area` | Right L5 multifidus ultrasound area; distinct from force and functional tests. |
| `muscle_performance` | `muscle_power` | Right-knee isokinetic power acquisition; existing ID retained for compatibility. |
| `muscle_endurance_test` | `muscle_endurance` | Separate right-knee fixed-load repetition test with its own completion bar. |
| `muscle_tone` | `muscle_tone`, `muscle_stiffness` | MyotonPRO outputs from the same marked right rectus femoris site and resting position; retain separate Hz and N/m values. |

The previous power/endurance card combined two different configured tasks:
power derived from an isokinetic dynamometer and endurance counted at a fixed
preflight load and tempo. Sharing a body region does not make these the same
test. Separate cards avoid marking both tasks complete when only one has been
performed. Each still uses its own indicator, personal baseline and detection.

The four eye cards remain separate because OCT thickness, clinician disc grade,
refraction and corrected acuity are different acquisitions. Within each card,
both eyes are entered separately; grouping never authorizes averaging eyes.
Tone and stiffness share acquisition but are not interchangeable or an atrophy
diagnosis. Legacy catalogue entries unrelated to the real problems and `_example`
fixtures are excluded from real check-in cards. All fourteen real problem
indicators occur exactly once across the nine cards.

## Method sources

- [Laughlin et al., NASA ISS isokinetic reliability, Methods/Table I](https://ntrs.nasa.gov/api/citations/20090019649/downloads/20090019649.pdf): instrumented isokinetic tasks. The configured power channel derives watts from torque and angular speed; this is not a repetitions-at-fixed-load measurement.
- [Hillen et al., Muscles 2026, Methods 2.3](https://www.mdpi.com/2813-0413/5/2/26): knee-extension repetition endurance. Fixed preflight absolute load is the project's longitudinal convention, not a new prescription from this grouping review.
- [MyotonPRO Quick Guide, measurement/results](https://myoton.com/wp-content/uploads/2025/01/Quick-Guide-A4.pdf): one device reports tone and stiffness. Site and positioning follow the existing indicator definitions.
- [NASA OCHMO-MTB-001, SANS](https://www.nasa.gov/wp-content/uploads/2024/02/ochmo-mtb-001-sans.pdf): different structural and visual examinations. Specific acquisition sources for each eye and muscle channel remain in `config/indicators.json`.
- Supplied `guia_breve_umbrales_atrofia_SANS.pdf`, pp. 1-2: compare like methods/sites and assess each eye independently. Grouping does not modify its criteria or the repository's baseline contract.

## Scope and remaining #98 work

This resolves the grouping review only. Existing `bar_full_hours = 24` values
remain v1 placeholders permitted by Ansel's latest #98 comment. They are not
approved universal medical testing frequencies. The new endurance card inherits
that same placeholder; no medical interval is inferred from a study's rest period.

Per-test intervals and their basis, sourced subjective-issue links, protocol
practice intervals and environment naming remain separate parts of #98. No
subjective links, clinical advice, thresholds or public function signatures change
here. Existing check-in IDs are retained; the endurance check-in adds one ID
under the existing configuration format. Old completion of the combined card
cannot establish completion of the newly separate endurance test.

Validation: `python -m core.config`; `python -m pytest`. Strict validation may
still report the separate, unresolved #98 content placeholders.
