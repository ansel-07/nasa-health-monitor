<!-- AI-assisted: written with Claude Code for Javi's bug hunt and reviewed by Javi. -->

# Bug hunt: Javi's part (#248)

Protocol engine, Protocols screen, Tutorials screen and protocol structure. Tested on `main` at `0baa36e` (v2 plus #253, #256): every protocol route walked through the engine (both problems × ISS/Moon/Mars × watch/urgency × every answer, no loops or dead ends), and in the browser at 1280×720 and at phone width (Firefox's minimum, about 500 px).

| # | Severity | Screen | Steps | Expected | Actual |
|---|---|---|---|---|---|
| 1 | Medium | Protocols | Open an urgent SANS protocol on Mars, select Done on "Stop risky tasks", then Main Menu → Change astronaut → same astronaut → Moon → Protocols. | The protocol says which environment it follows, or follows the new one. | The status bar says Moon Base, 1 s delay; the step caption says "Environment: Mars Base", and the routing (flight surgeon, 44 min round trip) stays Mars. Nothing explains why. |
| 2 | Low | Protocols, Tutorials (focused chart) | Urgent SANS on Mars, on "Contact crew medical officer" (`u_local`). | Only the exit that applies in this environment. | The chart shows both "Moon" and "Otherwise" arrows, although the environment check is automatic and only one can happen. |
| 3 | Low | Protocols (focused chart) | Urgent protocol, on the handover select "I can't" (`u_no_clinician`). | The way back to the handover is visible. | The return arrow is drawn on top of the "I can't" arrow, so it is hard to see. |
| 4 | Low | Protocols, Tutorials | Open any protocol step at phone width, then "Show whole protocol". | Readable flowchart text. | The focused chart text is about 8 px; the whole-protocol dialog shrinks the diagram to fit, so its text is smaller still. |
| 5 | Low | Protocols, Tutorials (focused chart) | Go through a few steps of any protocol. | Similar text size on every step. | Text size jumps between steps: a step with two boxes is drawn much larger than one with four, because the chart is scaled to the column width. |
| 6 | Low | Tutorials | Practise SANS with two astronauts whose stored measurements differ, giving the same answers. | The same answers take the same route. | Practice routes use the astronaut's real symptom levels (`core/protocol_engine.py:118`), so the concern branch can differ between astronauts. Documented behaviour, but surprising in a practice run. |
| 7 | Latent | Protocols | A protocol `measure` step where a later automatic step fails in the same submit (config error, storage error). | The value is stored once. | The value is stored and detected (`core/protocol_engine.py:230`) before the rest of the submit; if it then fails, the episode is not saved and the retry stores the value again. Neither real protocol has a `measure` step today. |
| 8 | Latent | Protocols | An `action` step with `wait_min`. | The wait can finish. | Waits use the mission clock, which only moves with "Advance mission 24 h", so "Refresh wait" never shortens it. No real protocol uses `wait_min`. |
| 9 | Latent | Protocols | An active episode whose protocol cannot load (invalid or removed config). | The astronaut is not blocked. | The screen says the protocol is unavailable (`pages/2_Protocol.py:137`) but the episode stays open, so every new alert for that astronaut goes to pending. Only after a config error. |

## Outside my part (for Ansel)

| Severity | Screen | Steps | Expected | Actual |
|---|---|---|---|---|
| Low | Protocols (end screen), `core/mascot.py` | Finish an urgent protocol with "Done" on the handover. | A calm, serious end after a medical urgency. | Lumi turns blue and smiles (the closed episode counts as nominal health state) right after a medical-urgency handover. |
