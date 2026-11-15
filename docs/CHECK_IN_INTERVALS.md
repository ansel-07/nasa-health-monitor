<!-- AI-assisted: generated with Codex and reviewed by Edu. -->

# Synthetic activity-bar timers (#98)

Edu explicitly selected "Use synthetic demo timers, clearly labelled as
non-clinical" on 2026-11-14. Every interval below is a **synthetic, non-clinical
activity-bar timer**. It is not an approved medical test frequency, treatment
schedule, confirmation wait or validated training-retention interval.

The numbers are project design choices, not numerical results from the sources.
The relative ordering reflects acquisition burden and the live-demo focus, not
the seriousness of a disease. Elapsed time means the simulated mission clock.

| Check-in | `bar_full_hours` | Equivalent days | Synthetic design basis |
| --- | ---: | ---: | --- |
| `eye_oct` | 720 | 30 | Slow instrumented structural-review bar; monthly demo cycle, not NASA's full surveillance calendar. |
| `optic_disc` | 720 | 30 | Same demo cycle for clinician image review; independent completion from OCT. |
| `refraction` | 720 | 30 | Same slow cycle for clinician refraction, independent of corrected-acuity entry. |
| `visual_acuity` | 168 | 7 | Faster functional-test bar for a weekly demo cycle. |
| `muscle_strength_test` | 168 | 7 | Weekly demo grip-review bar; not a clearance for maximal testing. |
| `muscle_size` | 336 | 14 | Slower instrumented ultrasound-review bar than the performance channels. |
| `muscle_performance` | 168 | 7 | Weekly demo power-review bar for its own acquisition. |
| `muscle_endurance_test` | 168 | 7 | Separate weekly repetition-test bar; does not prescribe recovery between tests. |
| `muscle_tone` | 168 | 7 | Weekly demo site-review bar for shared tone/stiffness acquisition; no empirically validated spaceflight cadence is asserted. |

| Protocol practice | `tutorial_bar_full_days` | Synthetic design basis |
| --- | ---: | --- |
| `sans` | 7 | More frequent demo practice for the selected live-presentation protocol. |
| `muscle_atrophy` | 14 | A contrasting slower demo practice cycle for the second protocol. |

Tutorial intervals deliberately differ from measurement intervals. They are
software practice cycles; they do not rank SANS as universally more urgent than
muscle problems. Existing rules still allow tutorial repetition only below the
configured 80-point threshold and never block active protocols or measurement.

These are full-to-empty bar durations, not minimum waits between activities.
With the existing 10-point steps, a tutorial first becomes repeatable at 70
points, after 30% of its full duration: 2.1 mission days for SANS and 4.2 for
muscle atrophy. That existing gate is unchanged; these are arithmetic consequences
of the synthetic timers, not additional training or medical recommendations.

## Evidence context and limits

- [NASA OCHMO-MTB-001, SANS, monitoring and testing overview](https://www.nasa.gov/wp-content/uploads/2024/02/ochmo-mtb-001-sans.pdf)
  describes mission-based surveillance and clinically indicated examinations.
  It does not validate these uniform monthly bar timers or protocol-practice
  periods. A scheduled exam is not the delay before confirming an anomaly.
- [NASA Exercise Overview, muscle assessment and ACERS supervision](https://www.nasa.gov/ochmo-tb-031-exercise-overview-2/)
  supports individualized monitoring and exercise planning, not one universal
  weekly timer for grip, power, endurance and myotonometry.
- Supplied `monitorizacion_astronautas_atrofia_SANS.pdf`, p. 10, proposes weekly
  functional reviews, ultrasound every 2-4 weeks and monthly OCT as prototype
  starting points. These are explicitly P proposals, not clinical validation.
  They provide design context for the synthetic weekly/fortnightly/monthly
  ordering; they do not establish every configured number.
- No reviewed source supplies an exact practice-review period for either
  configured protocol. The 7/14-day tutorial choices are solely demo policy.

New or worsening symptoms and medical instructions take precedence over a bar.
A full bar does not mean healthy or safe, and an empty bar does not diagnose a
problem. The app's existing confirmation timers and protocol content are unchanged.

## Implementation and scope

`core/activity.py` already reads each check-in's `bar_full_hours` and each
problem's `tutorial_bar_full_days`; no core or page change is needed. One advance
can therefore drain different bars by different amounts. The existing subjective
modifier applies to each check-in's own base timer, but subjective settings,
labels, values and links are untouched by this task.

Environment IDs, gravity and communication settings are unchanged. Display names
are now exactly **Moon Base** and **Mars Base**, as requested by the spec.

Validation: `python -m core.config --strict`; `python -m pytest`. Verify actual
per-test depletion using isolated activity storage and the mission clock.
