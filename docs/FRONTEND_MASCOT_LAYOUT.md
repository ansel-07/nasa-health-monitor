<!-- AI-assisted: generated with Claude Code and reviewed by Ansel. -->

# Frontend task: mascot-first layout (tonight, after P0 #1 and #2)

Owner: Ansel. Written for the coding agent that works alone tonight (`docs/TONIGHT_HANDOFF.md`).
Every decision below was **taken by Ansel**: do not re-open them. Where this file and `AGENTS.md` 8 / 16 or the
spec (`docs/ASTRONAUT_HEALTH_APP_SPEC.md` section 2) disagree, **this file wins**. The rules of
`TONIGHT_HANDOFF.md` section 1 (branches, self-review, merge, revert) and `AGENTS.md` 11 (no invented medical
content, English only, no new libraries, `AI-assisted` header) still apply.

## 0. The rule in one paragraph

The mascot is the centre of every astronaut screen. **Alone** (no chart or flowchart on screen) it is **big and
centred**, its subtitles under it, the buttons under the subtitles. When the screen shows **a chart or a protocol
flowchart** (and only then), the mascot **shrinks and slides to the left** with a smooth animation, and the visual
takes the right. Cards and buttons are **not** a visual: they always go below. **No mascot on Trends and Tutorials.**

| Screen (file) | Mascot | Visual on the right |
|---|---|---|
| Welcome (`pages/0_Home.py`) | big, centred, **full viewport** | none |
| Main Menu (`pages/5_Menu.py`) | big, centred | none (cards below) |
| Check-in list (`pages/1_Check_in.py`, list view) | big, centred | none (cards below) |
| Check-in detail (`pages/1_Check_in.py`, detail view) | small, left | the check-in's charts, stacked |
| Protocols, active step (`pages/2_Protocol.py`) | small, left | protocol flowchart |
| Protocols, any other state (finished, none active, pending only, waiting for repeat, error) | big, centred | none |
| Trends (`pages/3_Trends.py`) | **none** (already none: do not touch this file) | — |
| Tutorials, list and practice run (`pages/4_Tutorials.py`) | **none**, no voice toggle | flowchart full width (practice) |

Keep each screen in its current file and its current internal views (list/detail in `1_Check_in.py`,
list/practice in `4_Tutorials.py`). **Do not split pages into new files.** Do not change detection, episodes,
the protocol engine, activity bars or any `config/` content: this task is layout, mascot and navigation only.

## 1. Mascot module (`core/mascot.py`)

Public API stays exactly `say(text, mood="neutral", size="large")`, `beside(text, mood="neutral")`,
`voice_toggle()` (`AGENTS.md` 7). `build_html()` and `frame_height()` are internal and may gain keyword
parameters. Pages never write mascot HTML or mascot CSS.

### 1.1 Look

- The spec face, **no frame**: two cyan (`#5EF2FF`) rounded-rectangle eyes and a curved cyan smile drawn
  directly on the page background (`#111111`), like the SVG in spec section 2. Delete the black rounded square.
- Moods (`MOODS` in `core/models.py`, unchanged) change only the eye height and the mouth path, as today.
  Adjust the existing `_MOUTHS` / `_EYE_HEIGHT` values to the new `viewBox` so every mood is still recognisable.
- Keep the blink. `MASCOT_NAME` stays as it is (the name is a team decision for the morning).

### 1.2 Sizes

- **Big** face height = **35 % of the browser viewport height** (`window.parent.innerHeight`), about 380 px on
  a 1080p projector. **Small** = **45 % of big**. Subtitle font: **28 px** big, **18 px** small, line-height 1.45,
  centred, white on `rgba(0,0,0,0.72)` rounded box (as today).
- The iframe cannot use `vh` (it would be the iframe's own height). Inside the iframe, a script reads
  `window.parent.innerHeight`, sizes the face, then sets its own height with
  `window.frameElement.style.height = document.body.scrollHeight + "px"`. The `height=` passed to
  `components.html` is the fallback from `frame_height()` using **380 px big / 171 px small** faces.
  If the parent is not reachable, use those fallback pixel sizes.
- `beside()` keeps `st.columns([1, 3])` with the mascot column aligned to the top (#139).

### 1.3 Subtitles revealed word by word

- Render the **whole text** from the start, each word in its own `<span>` with `visibility: hidden`, so the
  subtitle box has its final size and nothing jumps. Reveal words in order.
- **Voice on:** reveal each word when the voice reaches it, using the utterance `boundary` events
  (`event.charIndex`: show every word whose start index is `<= charIndex`). If no `boundary` event arrives
  within **700 ms** after the utterance `start` event (some voices send none), switch to the timer below.
  On `end` (or `error`), show every word.
- **Voice off, or fallback:** one word every **330 ms** (about 3 words per second).
- While words are being revealed, the **mouth talks**: every 160 ms it alternates between the mood's mouth and an
  open mouth (a small rounded shape). When the last word is shown, it returns to the mood's mouth.
- Speech stays as today: `en-US`, the parent page's `speechSynthesis` first, then the iframe's; `cancel()` before
  speaking. Rendering a new mascot line cancels the previous speech.

### 1.4 Speak only when the text changes

- `st.session_state["mascot_last_text"]` holds the last text the mascot spoke/animated.
- On a render with the **same text** (any rerun: a toggle, a form error, a refresh of the same step), draw the
  subtitles **complete at once**, no voice, no talking mouth, no move animation.
- On a **different text**: speak (if voice on), reveal word by word, then store the text.
- Turning the **voice on** clears `mascot_last_text`, so the current line is spoken right away (useful on stage:
  one click on Voice and the mascot talks).

### 1.5 Move animation (centre ↔ left)

Streamlit re-creates the iframe on each page change, so the "move" is an **entry animation** done with CSS in the
parent page, not a persistent element.

- `st.session_state["mascot_layout"]` = `"large"` or `"small"`: the layout of the last mascot drawn.
- `say(size="large")` draws inside `st.container(key="mascot_alone")`; `beside()` puts the mascot column inside
  `st.container(key="mascot_side")` and the visual column inside `st.container(key="mascot_visual")`.
  The CSS selectors are the classes Streamlit gives keyed containers: `.st-key-mascot_alone`, etc.
- **Centre → left:** when `beside()` runs and the previous layout was `"large"`, inject (with `st.html("<style>…")`)
  an animation on `.st-key-mascot_side`: from `transform: translateX(150%) scale(2.22)` to `none`
  (the column is 1/4 of the width, so 150 % of its width moves its centre to the page centre; 2.22 = 1 / 0.45),
  **600 ms ease-in-out**, `transform-origin: center top`. The visual (`.st-key-mascot_visual`) fades in
  `opacity 0 → 1`, **300 ms ease-in, 300 ms delay**.
- **Left → centre** (symmetric): when `say(size="large")` runs and the previous layout was `"small"`, animate
  `.st-key-mascot_alone` from `transform: translateX(-37.5%) scale(0.45)` to `none`, 600 ms ease-in-out,
  `transform-origin: center top`.
- Inject the `<style>` **only on the run where the layout changes**, then set `mascot_layout`. On later reruns
  the style is not emitted, so the animation never replays; removing a finished animation leaves the element where
  it already is.
- Same layout as before (large → large, small → small): no animation.
- Respect `@media (prefers-reduced-motion: reduce)`: no animation.
- **Narrow screens** (`max-width: 768px`): Streamlit stacks the columns; the small mascot sits centred above the
  visual, no move animation (only the fade).

### 1.6 Voice toggle

- `voice_toggle()` draws the existing "Voice" toggle inside `st.container(key="mascot_voice")` and makes it
  `position: fixed; top: 0.75rem; right: 1rem; z-index: 1000` (top-right corner, every mascot screen).
- Call it once on Welcome, Main Menu, Check-in and Protocols. **Remove** it from Tutorials. Trends never had it.
- Remove the `st.columns([5, 1])` wrappers pages use today to place it.

### 1.7 Tests (`tests/test_mascot.py`)

Keep the existing tests passing (update the ones about the frame/size if the markup changes) and add:
every mood renders without the black frame; the text is fully present and escaped (word spans);
same text twice → second render has no speech and no reveal; voice turned on clears the last text;
`beside()` emits the move style only when the previous layout was `"large"`; `say(large)` emits the reverse
style only when it was `"small"`; `frame_height()` still grows with long texts.

## 2. Welcome (`pages/0_Home.py` and `app.py`)

**Full viewport, no scrolling, conversational buttons. No dropdowns and no NEXT any more** (this overrides spec
screen 1).

- `app.py`, only when the current page is Welcome, injects CSS that hides Streamlit's header and toolbar
  (`[data-testid="stHeader"]`, `[data-testid="stToolbar"]`), removes the top padding of the main block, and makes
  `.st-key-welcome_screen` `min-height: 100vh; display: flex; flex-direction: column; justify-content: center`.
  Other screens keep the header (this is not the browser Fullscreen API).
- The page draws everything inside `st.container(key="welcome_screen")`: the voice toggle (fixed top-right), the
  big mascot, then one row of buttons. Two steps, kept in `st.session_state["welcome_step"]`:
  1. Mascot: **"Hello! Who are you?"** (`happy`). One button per astronaut from `data.load_astronauts()`
     (label = `name`), in one row of equal columns.
  2. After a click: store `st.session_state["astronaut"]`, mascot: **"Hi {name}! Where is the mission?"**
     (`happy`). One button per environment from `config.load_environments()` (label = `name`), plus a secondary
     **"← Change astronaut"** button below that goes back to step 1. Clicking an environment stores
     `st.session_state["environment"]` and calls `st.switch_page("pages/5_Menu.py")`.
- Nothing is preselected: arriving at Welcome (first visit, or "← Back" from Main Menu) always shows step 1.
  Choosing a different astronaut replaces the context exactly as NEXT did (no other astronaut's data shown).
- Buttons are clickable immediately (no waiting for the speech); a click cuts the speech.
- Tests: rewrite `tests/test_home_navigation.py` for the two steps (no default, astronaut button → step 2,
  "← Change astronaut" → step 1, environment button → Main Menu with both keys set). Update the Welcome steps of
  `tests/test_check_in_seed_integration.py` and any other test that clicks `NEXT` or uses the Welcome
  `selectbox` (`grep -rn "NEXT\|selectbox" tests/`).

## 3. Main Menu (`pages/5_Menu.py`)

- Big centred mascot with the current text/mood logic (unchanged lines).
- Below the subtitles, in this order: the urgent-alarm `st.error` banners (unchanged text), then **one row of card
  buttons in equal columns**: `Protocols` (primary, only when it is visible today), `Check-in`, `Trends`,
  `Tutorials`. Card buttons: `use_container_width=True` and a min-height of about 4.5 rem (CSS on a keyed
  container, e.g. `st.container(key="menu_cards")`).
- `st.divider()` and the "Demo controls" expander stay at the bottom, unchanged (collapsed).
- "← Back" (to Welcome) from `app.py` is unchanged.

## 4. Check-in (`pages/1_Check_in.py`)

### 4.1 List view

- Replace `mascot.beside(...)` with `mascot.say(<same text>, <same mood>, size="large")`.
- Below it: the caption "Bars show time since completion…" and the check-in cards in a **3-column grid**
  (each card exactly as today: bordered container, name button, coloured bar). Then, in the current order, the
  subjective issues, the "Continue repeat measurement" / "Open Protocol" buttons and the waiting alerts.

### 4.2 Detail view

- **Remove the "Indicator" selectbox.** The visual on the right of the small mascot is **one compact chart per
  indicator of the check-in, stacked** (`charts.indicator_chart(..., compact=True, environment=...)`, same
  environment rule as today). In **repeat mode** (confirmation), show only the repeated indicator's chart.
- Everything that used the selected `indicator_id` outside confirmation (guidance-ready check, mascot "guidance
  not available" message) must now consider **every indicator in `field_ids`**. The form already has one input
  per indicator; keep it, keep "all values required" (it already rejects empty or non-finite values).
- Keep below the visual, full width and in the current order: problem state, symptom table, environment note,
  Open Protocol / Continue repeat, Finish check-in, wait info and "Simulate wait", the form, waiting alerts,
  subjective issues.
- Unchanged behaviour to preserve (already in v1): opening Check-in with an alert waiting for a repeat goes
  **straight to that check-in's detail in repeat mode**; the bar refills when the check-in session ends; a
  confirmed repeat **switches to Protocols automatically**.
- Error and "unavailable" states keep the big mascot (`say(..., size="large")`).

## 5. Protocols (`pages/2_Protocol.py`)

- Active step: unchanged (`beside()` with the flowchart; buttons below). It is the only small-mascot state.
- Every other state already uses `say(size="large")`: keep it. Remove the `st.title` only if it pushes the big
  mascot below the fold on a 1280×720 window; otherwise leave titles as they are on every screen.

## 6. Tutorials (`pages/4_Tutorials.py`)

- **No mascot and no voice toggle** anywhere on this page; remove the `mascot` import if unused.
- List: replace the `beside()` block with the intro text as a normal paragraph ("Practise each protocol here, so
  you know it before you need it. Nothing you enter is saved."), then the tutorial cards **in a 3-column grid**
  (each card as today: name, bar, Start button, captions).
- Practice run: caption "Practice: {name} · Nothing you enter is saved." (as today), then the **step text as
  `st.subheader`**, then the flowchart **full width** (with the "Show whole protocol" toggle), then the same
  buttons as today. Completed: `st.success` with the end step text plus the existing "Tutorial completed…" line.

## 7. AGENTS.md and the handoff

- In the first PR of this task, update `AGENTS.md` so it describes this layout: section 3 (screens, Welcome
  buttons), section 8 (mascot rules: big-centred alone, small-left only with a chart or flowchart, none on Trends and
  Tutorials, voice toggle top-right, speaks only on new text) and section 16 (remove the "cards on the right"
  override; add "Welcome uses conversational buttons, no dropdowns/NEXT"). Keep the rest of `AGENTS.md` intact.
- If the Welcome flow ends different from `TONIGHT_HANDOFF.md` section 4, update that demo script.
- Log each merged PR and any minor decision in `TONIGHT_HANDOFF.md` section 9.

## 8. Order of work and pull requests

Merge each PR yourself after the self-review checklist of `TONIGHT_HANDOFF.md` section 1. Run the app locally
(`streamlit run app.py`) at least once per PR and open every screen you touched.

1. `fable/mascot-core`: section 1 + the `AGENTS.md` update of section 7 above + tests.
2. `fable/welcome-menu-layout`: sections 2 and 3 + tests + handoff demo script.
3. `fable/check-in-layout`: section 4 + tests.
4. `fable/protocol-tutorials-layout`: sections 5 and 6 + tests.

If the token budget runs out, stop after a merged PR (never leave `main` half-done) and write what is left under
"Decisions for the morning".

## 9. Done when

- Welcome: on a 1280×720 and a 1920×1080 window, face, subtitles and buttons fit with **no scroll** and no
  Streamlit header; astronaut → environment buttons reach Main Menu; no dropdowns, no NEXT.
- Main Menu and Check-in list: big centred mascot, cards below; Check-in detail and an active protocol step:
  mascot slides from the centre to the left and shrinks (600 ms) the first time, never on later reruns; going back
  to a big-mascot screen animates the other way.
- Subtitles appear word by word (synced with the voice when it is on); the mouth moves while they appear; a rerun
  with the same text is silent and shows the full subtitles.
- Trends and Tutorials show no mascot and no voice toggle.
- `python -m pytest` and `python -m core.config --strict` pass; the 30-second demo of `TONIGHT_HANDOFF.md`
  section 4 still works end to end.
- Cannot be checked by tests (write in the night log for Ansel to check in the morning): the animation and
  word-by-word subtitles in Chrome, Edge and Firefox, and the voice.
