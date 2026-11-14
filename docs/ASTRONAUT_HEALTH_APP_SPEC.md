# Astronaut Health App — Implementation Specification for Codex

> **Purpose of this file:** Keep this Markdown document in the repository as the implementation reference for the application. Read it before modifying the code.
>
> **Product language:** **English only** for all user-visible text (navigation, forms, errors, charts, protocol and tutorial screens). This specification uses English to make the intended UI strings explicit.
>
> **Scope:** Build an achievable functional prototype by extending the existing repository, not a production-certified medical device.

## 0. Instructions for Codex / coding agents

1. **Inspect the repository first.** Identify its stack, entry points, routes/pages, existing health-check definitions, vital sign inputs and validation, protocol definitions, protocol priorities/severities, trend data structures, persistence, and tests. Reuse and adapt those systems instead of replacing them or assuming a specific framework.
2. **Use this document as the latest product specification.** It supersedes older plans involving points, scores, leaderboards, competition, avatars, or check-in tutorials. Do **not** implement any of those old concepts.
3. **Do not assume a fixed number of cards.** Every collection of check-ins, trends, protocols, and protocol tutorials must be driven by data and support an arbitrary number of items (including empty states). Existing repository definitions are the source of truth for their actual identities and quantities.
4. **Preserve the existing medical logic.** Get anomaly thresholds, protocols, recommended steps, severity/priority, and mappings from the repository or explicitly provided configuration. **Do not invent diagnosis thresholds, medical advice, protocol steps, or severity rankings.** If required clinical definitions are missing, expose the missing integration clearly, keep the UI testable with explicitly labeled demo fixtures only where appropriate, and report the gap.
5. **Do not create unsupported complexity.** Prioritize a functional, responsive, coherent MVP that six students could realistically develop/demonstrate in approximately two days. Use the repository's established style and dependencies where possible.
6. **Implement and test, not just describe.** After changes, summarize modified files, behavior implemented, checks run, and any unresolved configuration/clinical dependencies.
7. Avoid altering unrelated features, removing existing data, or adding major external dependencies without a strong reason.

## 1. Product overview

An English-language, dark-themed application for astronauts to manually record health measurements, detect objective anomalies using pre-existing repository rules, follow the appropriate protocols after a confirmed anomaly, review protocol tutorials, and examine historical trends.

The engagement mechanic is **four or more independent time-based progress bars** (depending on configured check-ins and tutorials), **not** points or competition. Each bar decreases in discrete 10-percentage-point steps. Completing the corresponding activity replenishes it to 100% under the rules below.

**Important interpretation:** A progress bar reflects how recently an activity was completed, **not** an astronaut's health status, a clinical risk score, or an assessment of their competence. It must not block medical measurement or access to an urgently needed protocol.

## 2. Visual design — follow the supplied reference images

The user supplied three UI references: a nearly black background, a bright cyan smiling face, and dark rectangular dropdown controls.

### Color tokens

| Token | Value | Description |
| --- | --- | --- |
| `background` | `#111111` | **Exact** background color sampled from the first reference image; use on all screens. |
| `accent` | `#5EF2FF` | **Exact** predominant cyan sampled from the smile image; use for the smile and enabled primary actions. |
| `surface` | `#2D2B27` | Dark control/card fill inspired by the third reference image; may be adjusted slightly for contrast. |
| `surfaceBorder` | `#4A4742` | Subtle outline for dark controls/cards, inspired by the third image. |
| `textPrimary` | `#EDEBE8` | High-contrast near-white text. |
| `textSecondary` | `#BDBBB8` | Muted secondary labels. |
| `disabled` | Neutral gray | Disabled `NEXT` button and disabled tutorial start actions. |

Use green → yellow → red progress-bar colors as remaining percentage drops. Exact stop colors are a **UI implementation choice**, not clinical categories. Maintain readable contrast, visible keyboard focus, and color-independent status labels.

### Smiling face

- Recreate the supplied **simple cyan smiling face** (two rounded rectangular eyes and a curved smile, **without** a surrounding face circle), on the black background.
- It should be **large**, centered horizontally and positioned somewhat **above the vertical center** on the Welcome screen.
- On the Main Menu, Check-in list, and Tutorials list, the same face becomes **smaller and moves to the right**; the clickable card collection sits around the middle, slightly left of center.
- A lightweight CSS transition between Welcome and Main Menu is desirable, if compatible with the framework; basic accurate positioning matters more than animation.
- **No smiling face on the Trends page.**
- Use the supplied image as a visual reference. If the file is not included in the repo, implement the shape as a small inline SVG or CSS drawing using the exact cyan token; do not depend on a nonexistent asset path.

The images supplied in the conversation are **not automatically available to Codex in the repository**. A self-contained SVG approximation of the face is provided below so the implementation does not depend on those attachments:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122 120"
     fill="none" aria-hidden="true">
  <rect x="13" y="29" width="30" height="26" rx="9" fill="#5EF2FF"/>
  <rect x="80" y="29" width="30" height="26" rx="9" fill="#5EF2FF"/>
  <path d="M24 87 Q61 119 99 87" stroke="#5EF2FF"
        stroke-width="9" stroke-linecap="round"/>
</svg>
```

This SVG is an approximation of the reference, not a new product requirement; adjust its proportions if the original image is later added to the repo.

### Cards and global layout

- Navigation items appear as **clickable dark boxes**, with a treatment modeled after the supplied dropdown screenshot (dark fill, subtle border, rounded corners, white text); **do not make navigation cards look like editable form inputs**.
- Card counts are dynamic. Render a responsive stack/grid with consistent spacing that works with 1, 2, 3, or many items without overlap or clipped content.
- The Welcome screen uses labeled **dropdowns** like the reference; the other screens use navigation/expansion cards.
- Back buttons should be consistently located **top-left** wherever specified.
- Avoid distracting animations, complex mascots, badges, scores, and unnecessary gamification UI.

## 3. Navigation / screens

Implement the following conceptual screens. Whether they are separate routes or in-app views depends on the existing codebase.

```text
Welcome
  └── NEXT (only after both selectors are manually chosen)
       └── Main Menu
           ├── Check-in
           │   ├── Check-in list
           │   │   ├── Check-in detail (instructions + manual values)
           │   │   └── Subjective issues selector (at bottom)
           │   └── If objective anomaly is confirmed on repeat → Protocols
           ├── Trends
           │   └── Expand chart inline from its card (no separate graph page)
           └── Tutorials
               └── Protocol tutorial detail

Protocols (conditional destination only after second anomalous check)
  └── Pending protocol(s), ordered by repository-defined priority
```

All three Main Menu destinations must offer a way back to **Main Menu**. Check-in detail and tutorial detail should return to their respective list pages. After entering Protocols, provide sensible navigation back to the relevant health context while preserving pending-protocol state.

### Screen 1 — Welcome / identity and mission

**Visual structure:** large cyan smile high-center; below it, two labeled dropdown selectors arranged side by side on desktop, stacked on narrow screens.

- First label: **`Who are you?`**
- First dropdown options: **`Astronaut A`**, **`Astronaut B`**, **`Astronaut C`**.
- Second label: **`Where is the mission?`**
- Second dropdown options: **`International Space Station`**, **`Moon Base`**, **`Mars Base`**.
- **No preset/default selection** is allowed in either dropdown. Each must have a placeholder, e.g. `Select astronaut` / `Select mission`; the user must intentionally choose both.
- A **`NEXT`** button sits at the **bottom-right**. It starts disabled and gray. Only after **both** selectors contain user selections does it become enabled and cyan (`#5EF2FF`). Clicking then navigates to Main Menu.
- The app must retain the selected astronaut and mission as active session context. Changing the astronaut must not display another astronaut's private measurement history, bar states, symptoms, or pending protocols.

### Screen 2 — Main Menu

- Smile is **smaller, on the right**.
- A clickable-card column/group appears around the center-left, initially with these **three navigation labels** (exact UI text):
  - **`Check-in`**
  - **`Trends`**
  - **`Tutorials`**
- Clicking each card navigates to the relevant screen.
- Top-left back button returns to **Welcome**.

### Screen 3 — Check-in list and individual check-ins

**Check-in list**

- Top-left back button returns to Main Menu.
- Small cyan smile remains on the right, as on Main Menu.
- The dynamic list of objective health check-ins appears as clickable cards in the same center-left area as the Main Menu cards.
- Each check-in card shows its name and **its own time-based progress bar underneath**.
- The actual check-in types, form fields, units, clinically meaningful ranges, anomaly rules, and associated protocols must come from the **existing repository** where available. Do **not** assume exactly two check-ins or invent clinical checks.
- Clicking a card opens a **check-in detail** screen with a clear explanation of how to perform that check-in and the applicable **manual numeric/data entry fields**. Use repository content/instructions for the examination; do not invent medical procedure instructions.
- Validate required fields, input formats, and units; keep errors clear and in English. A reading's medical value **must not affect bar color**, which only indicates timing since completion.

**Two-pass verification of an objective anomaly**

1. The astronaut submits a complete check-in.
2. Run the repository-defined objective anomaly detection for that check-in.
3. If the result is normal, save the record and complete the check-in.
4. If an anomaly is detected, tell the astronaut the measurement needs to be **repeated** to rule out a possible measurement/entry error. Show the relevant check-in form again for a **second independent submission**, keeping a record of both measurements.
5. If the **second measurement does not confirm the issue**, do not launch a protocol from that first anomaly. Save the check-in session and explain that the repeat did not confirm the result.
6. If the **second measurement also triggers an anomaly**, create/activate the linked protocol(s) using repository rules, then redirect to the **Protocols screen**.
7. Do not let page refresh, Back/Forward, or double-clicking create duplicate protocol instances for the same confirmed event.
8. On completion of the check-in session, refill that check-in's bar to **100%**. Never use the bar as a gate that prevents the astronaut from taking a necessary measurement.

**Safety constraint:** The two-reading confirmation is a *prototype product rule*, **not clinically validated triage**. If the repository already defines an urgent/escalation exception, **preserve it**; real safety-critical scenarios must not be delayed merely to complete a second entry. Avoid claiming the app is medically approved.

**Subjective issues — dropdown below all objective check-in cards**

- Under the entire check-in card list, show an **expandable dropdown/panel** with a list of **subjective issues/symptoms**, independent of the objective readings. The astronaut may select one or multiple issues they are experiencing that might not appear in a measurement.
- Record the selected subjective issues with timestamps and the astronaut context so the app can detect persistence across multiple days.
- At the **end of each check-in detail**, offer an **optional way to report an additional subjective issue**, in addition to the main check-in-list selector. Both entry points should save to the same underlying symptom history, without duplicate submissions.
- Persistent subjective issues should cause the bar of the **most closely associated objective check-in** to **decrease faster** so that the relevant check-in is prompted more often.
- Source the **issue-to-check-in association** from the repository or explicit configuration, rather than guessing clinical mappings. Persistence duration and acceleration factor must also be configurable (see §6). A subjective issue does **not** itself automatically trigger the objective two-reading-to-protocol flow unless existing medical rules explicitly require that.
- Allow editing/clearing an issue when it is no longer present; do not treat merely opening the issue dropdown as a report.

### Screen 4 — Trends (inline expanding charts)

- Top-left back button returns to Main Menu.
- **Do not show the smiling face** on this screen.
- Center a dynamic collection of dark clickable cards, one per metric/trend available from the repository or measurement history.
- Clicking a metric card expands/reveals its corresponding **chart directly below or inside that same card** (accordion/inline expansion). **Do not navigate to a separate Trends chart page.** Clicking again can collapse it.
- Charts use the manually recorded check-in measurements with timestamps and readable labels/units. Filter by active astronaut, and respect how the repository scopes mission context.
- If no measurements exist for a metric, show a clear English empty state such as `No measurements yet` rather than invented sample values presented as real data.
- Keep graphs simple and responsive; use an already-installed charting library if suitable, otherwise lightweight existing project facilities.

### Screen 5 — Tutorials (only for protocols)

- Top-left back button returns to Main Menu.
- Small cyan smile on the right, with tutorial cards in the center-left, using the same layout as Main Menu / Check-in list.
- Provide **one tutorial per available protocol**; number of tutorials is dynamic and mirrors available configured protocols. **No check-in tutorials.**
- Each tutorial card shows the protocol/tutorial name and its own **time-based progress bar**, styled like check-in bars.
- The tutorial may be **performed/completed again only when its bar is strictly below 80%**. With 10-point steps, that means **70% or lower**. When bar is 80–100%, its `Start tutorial`/`Repeat tutorial` control should be disabled and show an explanatory hint.
- Completing the tutorial resets its own progress bar to **100%**.
- A knowledge-check question at the end is **optional**; it is not required to mark the tutorial complete or refill its bar.
- Tutorial content and any protocol descriptions must come from the repo. Do not generate unverified clinical instructions.
- Keep medical protocol guidance accessible through the actual **Protocols** flow when it is needed; tutorial cooldown must **never** block an emergency/active protocol.

### Screen 6 — Protocols (conditional; not a Main Menu option)

- This screen is **not** a permanent Main Menu destination.
- It opens only after the check-in's second objective reading confirms an anomaly, subject to existing urgent clinical escalation rules in the repository.
- Show the active/pending protocol(s) and allow the astronaut to open the appropriate **step-by-step workflow** for each one.
- If several protocols are pending, display them **top-to-bottom from highest to lowest priority/severity**, using **the severity definitions and ordering already present in the repository**. Do not invent priorities or infer severity from presentation color.
- Track each pending protocol's status according to the existing app model; do not silently discard protocols when the user navigates away. Avoid adding unverified treatment steps.
- Use clear English status/action labels and make the UI usable without relying solely on color.

## 4. Progress-bar behavior (shared system)

Each check-in and protocol tutorial has an **independent** bar with identical visual mechanics but potentially different configurable depletion intervals.

### Shared rules

- Allowed values: **`100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0`** only.
- Bar decreases by **10 percentage points** each time its configured time interval elapses. It never decreases below **0%**.
- Green when relatively full, yellow around the middle, red near the end. These are **activity-recency indicators only**; include a text label for accessibility.
- Check-in bar returns to **100% when a check-in session is completed** (see two-pass flow). The check-in form must remain usable at any bar level.
- Tutorial bar returns to **100% when the tutorial is completed**, but **repeating a tutorial is gated at `< 80%`**.
- A bar at 0% means the activity is due/overdue for this prototype, **not** that a medical emergency or poor health has been detected. Do not penalize the astronaut or disable features.
- Save state reliably across refreshes/restarts, **separately for each astronaut**. Time calculations must use actual timestamps rather than resetting on page reload or app reopening.
- Calculate elapsed steps from persisted time data; no constantly running background timer is required. Refresh the display on view load/focus and optionally on a lightweight periodic UI refresh while open.
- The visual text and percentage must correspond to the same computed value.

### Basic calculation without symptom-related acceleration

For each bar with a previous completion timestamp:

```text
elapsed = max(0, now - lastCompletedAt)
stepCount = floor(elapsed / configuredStepDuration)
percentage = max(0, 100 - stepCount * 10)
```

Use proper UTC timestamps and render in local user time when necessary. Guard against invalid or future timestamps.

### Initial state

**Proposed MVP behavior (not explicitly specified by the product owner):** If an activity has **never been completed**, its bar is **0% / Not completed yet** so that the astronaut can immediately complete a new tutorial and carry out an initial check-in. On completion, the bar becomes 100% and normal depletion begins. Do not accidentally start a brand-new tutorial at 100% and make it impossible to open for days due to the `<80%` rule.

### Timing configuration — do not mistake prototype defaults for clinical requirements

Define the time per 10-point step centrally and per activity if the repository allows it. **The user has not finalized timing values.** For a working demonstration only, earlier brainstorming used the following *optional defaults*:

| Activity | Demo step interval | Full 100→0 duration |
| --- | --- | --- |
| Check-ins | 2.4 hours per 10 points | 24 hours |
| Protocol tutorials | 24 hours per 10 points | 10 days |

These are **UI/demo parameters, not medically approved frequencies**. Prefer existing repository settings if they exist; keep them easy to change. Do not introduce clinical claims based on these timings.

### Subjective-issue persistence and acceleration

**Product intent:** If an astronaut reports a subjective issue on several days, the related check-in's activity bar should deplete faster to encourage more frequent measurement.

Implementation requirements:

- Record issue history (issue ID, astronaut ID, time/date, whether still active/resolved).
- Use a **configurable** number of calendar days to qualify as persistent (not yet specified by the product owner).
- Use a **configurable** increase in depletion rate for the linked check-in(s) (not yet specified).
- Apply acceleration **only** to the associated check-in bars, **not** tutorial bars. Cap the result to `0..100` and retain 10-point steps.
- Make acceleration deterministic across reloads. Do not retroactively accelerate the entire past interval if an issue became persistent only recently; preserve any rate-change timestamps or a small depletion-event/history ledger if needed.
- When a problem is marked resolved, restore the base depletion rate for **future** time; do not magically refill an already depleted bar.
- Do not activate acceleration for an unmapped issue; show/log that the issue-to-check-in mapping needs configuration.

**Clearly labeled implementation-only defaults if no repository configuration exists:** `persistenceDays = 3` consecutive calendar days and `depletionSpeedMultiplier = 2`. These are **demonstration placeholders only**, not medical decisions; expose as editable constants and mention them in Codex's implementation report. If the repo contains different rules, use those instead.

## 5. Suggested data contracts (adapt to the repository)

Do **not** impose a new database or a specific schema if the codebase already has one. The following are conceptual entities/fields to ensure persistence and per-user isolation:

```text
SessionContext:
  astronautId
  missionId

CheckInDefinition:
  id, displayName, instructions, inputFields, units
  anomalyDetectionRule (from existing repository)
  linkedProtocolIds (from existing repository)
  linkedTrendMetricIds
  depletionStepDuration

MeasurementRecord:
  id, astronautId, missionId, checkInId
  timestamp, submittedValues, validationStatus
  checkSessionId, attemptNumber (1 or 2), anomalyResult

CheckInSession:
  id, astronautId, missionId, checkInId
  startedAt, completedAt, status
  firstMeasurementId, secondMeasurementId (optional)
  confirmedAnomaly, generatedProtocolInstanceIds

ProtocolDefinition:
  id, title, medicalInstructions (existing content)
  priorityOrSeverity (existing repository ordering)

ProtocolInstance:
  id, astronautId, missionId, protocolId
  relatedCheckSessionId, status, createdAt, completedAt

TutorialProgress:
  astronautId, missionId, protocolId
  lastCompletedAt, completionCount

ActivityBarState:
  astronautId, missionId, activityType, activityId
  lastCompletedAt and/or depletion events needed for rate changes

SubjectiveIssueDefinition:
  id, label, associatedCheckInIds (from repo or explicit config)

SubjectiveIssueRecord:
  id, astronautId, missionId, issueId
  reportedAt, activeOrResolved, source (checkInList or checkInDetail)
```

**Mission scoping:** Mission is selected on Welcome and must be preserved/displayed in context. The product owner has not explicitly defined whether histories are shared across missions for the *same astronaut*. Use existing repository behavior if present; otherwise prefer isolation by `(astronautId, missionId)` for the prototype and document that decision. Under no circumstances mix different astronauts' records.

For a small local demo, an existing repository persistence mechanism or local browser storage may be sufficient, but if a backend/multi-device architecture already exists, integrate with it instead of creating a contradictory second data store.

## 6. Key interactions and edge cases

- **Selection gating:** `NEXT` stays disabled if either selection is unset; placeholders are not valid selections. Back to Welcome should allow changing selection intentionally.
- **No fixed counts:** 0, 1, 2, 3, or many cards must not break layout. If none exist, present a helpful English empty state.
- **Repeat measurement:** Preserve both objective readings and clearly show when a repeated measurement is requested. A normal second reading cancels the new protocol activation for that session.
- **Confirmed anomaly:** Create linked protocol instance(s) idempotently, navigate to Protocols, and sort by existing severity priority.
- **Multiple pending protocols:** Show all and retain them; do not show only the newest.
- **Charts:** Use real stored values only, not fabricated measurement points. Handle no history, few points, and many points.
- **Subjective issues:** Allow multiple selections, optional report at end of check-in, longitudinal persistence, mapped acceleration, and resolution without duplicating issues from simultaneous entry points.
- **Bars:** Correct boundary behavior at exactly 80%, just below 80%, 100%, and 0%; no negative values or fractional visual percentages. Different activities deplete independently.
- **First-time tutorial:** Must be available without waiting for the initial cooldown (see proposed initial state).
- **Context change:** Switching astronaut/mission must update histories, active protocols, and bar states to the correct context.
- **Navigation:** No blocked access to check-ins or active medical protocols because of progress-bar status. Handle Back and refresh without losing an in-progress confirmation state if practical.
- **Errors and accessibility:** Clear English validation messages, usable keyboard navigation, sufficient contrast, buttons with discernible labels, expandable chart state announced accessibly, visible focus, and responsive layouts.

## 7. Implementation priorities for the two-day MVP

### P0 — essential

1. Inspect the repo and wire up its existing check-in/protocol definitions and priorities.
2. Implement English-only Welcome with exactly 3 astronaut options, exactly 3 mission options, proper disabled/enabled `NEXT`, and active context.
3. Implement Main Menu and working navigation/back actions.
4. Apply reference visual style: `#111111` background, cyan smiling face, dark rounded cards and buttons.
5. Implement dynamic Check-in list, detail instructions/manual entry, repository-defined anomaly detection, second measurement, conditional protocol activation, and protocol priority ordering.
6. Implement dynamic Tutorials list with one tutorial per protocol and the strict below-80% rule.
7. Implement time-decaying independent 10-point progress bars and persist per astronaut.
8. Implement Trends with inline expanding charts and honest empty states.
9. Implement subjective issues input and persistence plus a configurable, mapped acceleration path.

### P1 — polish only if P0 is stable

- Smooth resize/reposition transition for smile.
- Subtle hover/press feedback and refined responsive spacing.
- Optional tutorial knowledge question (never mandatory for completion).
- Clear contextual labels for bar refresh eligibility and upcoming activity.

No points, leaderboards, achievement system, avatars, additional check-in tutorials, chatbots, or unrelated features.

## 8. Acceptance criteria / manual QA checklist

- [ ] All visible application UI text is in **English**.
- [ ] All page backgrounds use **`#111111`**; smile and enabled primary actions use **`#5EF2FF`**.
- [ ] Welcome shows a large upper-center smile, two correctly labeled dropdowns, and a bottom-right `NEXT` that is gray/disabled until **both** values are manually chosen.
- [ ] Welcome has exactly three astronauts and three missions as listed.
- [ ] Main Menu shows smaller smile on the right, `Check-in`, `Trends`, `Tutorials` cards on the center-left, and Back top-left.
- [ ] Check-in list shows dynamically sourced check-ins, each with a 10%-step bar, plus an expandable subjective-issues selector **below** all cards.
- [ ] Check-in detail explains the procedure, accepts manual values, validates entries, and offers extra subjective-issue reporting at the end.
- [ ] First abnormal objective reading requests a second measurement; a nonconfirming second result does not launch a new protocol; a confirming second result launches the linked protocol(s).
- [ ] A completed check-in refills its bar to 100%, and necessary check-ins remain available regardless of bar state.
- [ ] Multiple confirmed/pending protocols appear ordered according to the **existing repository's severity/priority**, with step-by-step content from that repository.
- [ ] Protocols screen does not appear as a general Main Menu link.
- [ ] Trends shows centered dynamic cards and expands each chart **within the same screen**; smile is **absent**.
- [ ] Tutorials shows a dynamic card per protocol, each with a bar. It does **not** contain check-in tutorials.
- [ ] Tutorial repeat/completion is disabled at **80–100%** and enabled at **70% or less**, as well as when never completed (with the proposed 0% initial state).
- [ ] Completing a tutorial resets only that tutorial's bar to 100%. A final question, if implemented, is optional.
- [ ] Bars step down by 10 points over time; turn visually green/yellow/red with decreasing recency; do not go below 0; remain correct after refresh and switching astronaut.
- [ ] Persistent mapped subjective issues accelerate only the related check-in bar; clearing an issue stops future acceleration.
- [ ] The design remains usable with any number of dynamic cards and at narrow viewport sizes.
- [ ] Existing tests/build pass; key new behaviors have tests or documented manual checks.

## 9. Product decisions still to confirm (do not quietly present assumptions as requirements)

1. **Exact check-in, protocol, trend, and subjective-issue definitions:** obtain from repository; no fixed card count.
2. **Bar timing:** exact duration of each 10% drop per activity is not finalized. Defaults in §4 are demonstration examples only.
3. **Subjective persistence:** exact number of days, issue-to-check-in mappings, and speed increase are not finalized; any defaults in §4 are explicitly provisional.
4. **Mission-level data ownership:** whether switching missions preserves or separates histories for a given astronaut is undecided; use repo behavior or the documented MVP assumption.
5. **Unanswered medical details:** never fabricate numerical abnormality thresholds, actual treatments, or protocol priorities. Report missing requirements instead.
6. **First-use bar value:** 0% until first completion is a proposed MVP choice to avoid locking new tutorials; confirm later if desired.
7. **Tutorial final question:** optional content only; do not make it a blocker or time-consuming dependency.

## 10. Expected Codex completion report

After implementing, report:

- The repo stack and which pre-existing definitions/rules were reused.
- The pages/components/modules created or modified.
- The data persistence strategy and the astronaut/mission scoping choice.
- Which requirements are implemented, partial, or blocked.
- Any explicitly assumed **demo-only** timings or subjective-issue settings.
- Build/test commands run and their results.
- Any missing clinically validated input/rules requiring project-owner follow-up.

**End of specification.**
