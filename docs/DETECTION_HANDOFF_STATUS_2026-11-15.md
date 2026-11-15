<!-- AI-assisted: generated with Codex for Juan Carlos; human review pending. -->

# Detection handoff status: 15 November 2026

This is the current execution status of the supplied Sunday Detection plan.
Use current `AGENTS.md`, `docs/UI_STYLE.md` and configuration for implementation.
The older plan's descriptions of missing features and large centered mascots
outside Welcome are historical, not new implementation requirements.

## Snapshot and authorization

- Refreshed base: `057bb51` on `origin/main`.
- Source implementation tested: `59b43ac`, branch `juancarlos/persistent-check-in-alarm-details`.
- No open `to:juancarlos` requests were returned at task start. #187 and #200 are closed after #215.
- Normal ownership applies. Ansel reviews and merges; the Saturday solo exception was not extended.
- This change is limited to Check-in presentation, its tests and this status document.

## Plan reconciliation

| Plan item | Current status and evidence |
| --- | --- |
| D00: refresh | Complete: current GitHub requests, main, instructions and team deliveries checked. |
| D10: measure performance | Previously delivered and verified in #213: local median 0.5169 -> 0.3553 seconds, with equivalent episodes, pending alerts and latest values across three environments and four advances. These are historical local measurements, not deployed timings. |
| D11: configuration cache | Deferred by the plan's measurement gate. Earlier profiling found config loading was a small cost; no new evidence justifies editing Ansel's loader. |
| D12: detection work | Justified baseline reuse delivered in #213. Public validation still checks every condition branch. Broader validation/result caches remain unnecessary for the measured local workload. |
| D13: episode/storage overhead | Delivered in #205, #207, #209 and #213: retryable confirmation, equal-time evidence/replay handling, dismissal snapshots and narrower duplicate scans. Existing data contracts retained. |
| D20: persistent alarms | Remaining work implemented for review in this branch: configured actions and urgent narration persist in list and detail, including with an objective episode or saved reading. History failures are visible; unavailable recency is not displayed as zero. |
| D30: Check-in layout | Already delivered: compact assistant line under the current style, cards below it, grouped forms and stacked charts beside the small mascot. Repeat mode keeps the original indicator and environment. No redesign needed. |
| D40: subjective details | Approved structure already delivered; reviewed wording applied by #215. Five configured alarms include ALM_05 from #194. Additional onset timestamps or explicit yes/no/unknown answers remain outside the approved schema. |
| D50: static symptom snapshot | Existing static table and return-to-list behavior retained; automated regressions pass. Browser double-click/scroll acceptance remains unverified in this task. |
| D60: responsive/voice checks | Manual acceptance remains: narrow/projector layouts, focus, scrolling, speech and animation. AppTest is not a real-browser check. |
| D90: release checks | Automated checks below passed. Current branch still requires Ansel's review and the remaining manual acceptance. |

## Remaining-work implementation

- Read the selected astronaut's issue history once per page run and share it with the report panel.
- Keep each active alarm's exact configured label and action visible in both Check-in views.
- Preserve urgent narration alongside baseline warnings, storage errors and objective confirmation/protocol controls.
- Preserve alarms after a successful measurement; only explicit resolution clears them.
- On issue-history errors, show the failure, disable unavailable report controls and omit misleading recency bars. Check-in navigation and measurement entry remain available.
- Keep all runtime persistence in existing core APIs. No health thresholds, public signatures, episode statuses or dependencies were changed.

## Verification

- `.venv\Scripts\python.exe -m pytest tests/test_check_in.py tests/test_check_in_mission_integration.py tests/test_subjective_symptoms.py`: **149 passed**.
- `.venv\Scripts\python.exe -m pytest`: **1162 passed** on the source implementation above.
- `.venv\Scripts\python.exe -m core.config --strict`: **OK**.
- `git diff --check`: passed.
- Local Streamlit startup: HTTP health response **200 ok**, server stopped afterwards.
- New coverage includes both views, pending/active episodes, warnings/errors, successful recording, astronaut isolation, explicit resolution, real storage and corrupt activity JSON.
- Full regressions include the real-seed demo, session isolation, pending queue, failure recovery and reset.
- No real-browser, voice-listening or deployed latency checks were performed. No runtime or seed files were changed by this task.

## Next review

Review this branch against main, then verify the configured alarm action remains visible while opening a check-in, recording a normal reading, returning to the list and explicitly resolving the alarm. Complete the manual checks above before claiming visual/voice acceptance.
