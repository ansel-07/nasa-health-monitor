# UI style · "mission console + clinical"

> AI-assisted: generated with Claude Code and reviewed by Ansel.
> Decided by Ansel. Owner: Ansel. Applies to every screen; `AGENTS.md` sections 3 and 8 point here.

The app must look like real mission software, not a template. Dark night-blue surfaces like a mission console; the calm spacing and clarity of a clinical app.

## Rules

1. **No page titles.** No screen shows `st.title` / `st.header`. Context comes from the mission status bar, the mascot's line and small section labels (`st.subheader`, styled as monospaced upper-case labels).
2. **Mission status bar** on every screen except the Welcome (`core/ui.py`, drawn by `app.py`): astronaut · environment · mission day · mission time · one-way signal delay, next to the back button.
3. **No Streamlit chrome.** No header, toolbar or menu (`.streamlit/config.toml`: `ui.hideTopBar`, `client.toolbarMode`). Content is centred, at most 1100 px wide.
4. **Colours** (theme in `.streamlit/config.toml`, constants in `core/ui.py`):

   | Token | Value | Use |
   |---|---|---|
   | background | `#0B1220` | page |
   | surface | `#131C2E` | cards, expanders, metrics |
   | border | `#22304A` | borders, grid |
   | text / muted | `#E6EDF7` / `#7C8BA5` | text / labels, captions |
   | accent | `#5EF2FF` | the mascot, primary actions, mission data |
   | normal / watch / urgency | `#3DDC97` / `#FFB547` / `#FF5C5C` | status, always with a text label |

5. **Type:** IBM Plex Sans for text, IBM Plex Mono for numbers, labels and the status bar (served from `static/fonts/`, SIL Open Font License, no external font service).
6. **Icons:** Material Symbols built into Streamlit (`icon=":material/...:"`). **No emojis.**
7. **Tone:** data and labels short and operational ("Repeat after 08:10"); the mascot stays friendly.
8. **Motion:** subtle only (content fade-in, a few pulses on urgent alerts); nothing moves with `prefers-reduced-motion`.
9. **NASA:** space-agency style without NASA logos or anything implying endorsement; a single footnote "Built for NASA Space Apps 2026".
