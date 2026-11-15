<!-- AI-assisted: implemented with Codex from copy supplied by Gonzalo; integration review pending. -->

Implementation scope: messages 1–32 are applied to pages for #222. Protocol sections 5–8 below are a product proposal for Edu under #223; they are NOT applied to runtime configuration. Existing clinical rules, safety-on-storage-failure handling, and all protocol files remain unchanged. The protocol proposal predates extra nodes added in #195/#224 and must be adapted by Edu before activation.

# MASCOT DIALOGUES — SHORT VERSION

## 1. WELCOME

**1.** Hey! Who's joining?

**2.** Hey {astronaut}! Where's our mission?

## 2. MAIN MENU

**3.** Alright, {astronaut}. What's the plan?

**4.** {astronaut}, an alert needs another measurement in Check-in.

**5.** You've got a protocol to follow, {astronaut}.

**6.** Hey {astronaut}, {number} alert(s) need your attention.

**7.** You've reported an urgent symptom. Stop the risky task and contact the crew medical officer now.

## 3. CHECK-IN

**8.** Pick a check-in. Let's record your measurements.

**9.** Let's record this check-in's measurements.

**10.** Hmm, {problem} needs another measurement to confirm it.

**11.** Your alert's confirmed. Open Protocol for the guided steps.

**12.** We're missing some assessments. See the warnings below.

**13.** Let's repeat the indicated measurement to confirm the alert. Check the warnings below for incomplete assessments.

**14.** Alert confirmed. Open Protocol to continue. Some assessments are incomplete; check the warnings below.

**15.** Measurement guidance isn't ready yet. We can't submit this check-in.

**16.** The measurement setup isn't complete, so check-in submissions aren't ready yet.

**17.** First, choose your astronaut and environment on Home.

**18.** Sorry, Check-in isn't available with this selection.

**19.** This episode can't be opened in Check-in.

**20.** You've reported an urgent symptom. Stop the risky task and contact the crew medical officer now.

### CHECK-IN ERRORS

**21.** Check each indicator: enter a finite measured value before submitting.

**22.** Couldn't complete a task? It needs an immediate safety assessment, even at low intensity.

**23.** Urgent symptom: {symptom}. Act now: {action}

**24.** Couldn't save the details. {error}

**25.** Some issue changes didn't save. Check your selection and retry. {error}

**26.** Measurements recorded, but completion didn't save. Try Finish check-in again. {error}

**27.** Mission time moved forward, but detection didn't finish. {error}

## 4. PROTOCOLS — GENERAL MESSAGES

**28.** Choose your astronaut on Home first.

**29.** No astronaut protocol for this issue. Let's not guess.

**30.** We need a repeat measurement before this protocol can start. Head to Check-in to confirm the issue.

**31.** No active protocols right now.

**32.** I can't start this protocol: required information is missing or invalid. Please ask the mission team for help.

---

## 5. SANS PROTOCOL — MONITORING AND FOLLOW-UP

**Step 1 — Check for warning signs**

Any warning signs in either eye: a new visual-field gap, central distortion, correction needed beyond what's available, sudden vision loss, severe eye pain, or severe headache with neurological signs?

**Step 2 — Notify the crew medical officer**

Bring in the crew medical officer. Agree together on check-ups and who's responsible for each.

**Step 3 — Request priority medical review**

This needs a closer look. Ask the crew medical officer for priority medical review of the finding. A concerning number alone doesn't establish urgency.

**Step 4 — Review test results**

With your clinician, review corrected acuity and each eye's personal baseline using Check-in results. Review OCT and visual fields if available. Missing or invalid tests mustn't be treated as normal.

**Step 5 — Tests unavailable**

Tell the crew medical officer which eye results are unavailable or invalid. Arrange an appropriate assessment; without OCT, structural surveillance is incomplete.

**Step 6 — Follow-up guidance**

Use only prescribed optical correction and follow sleep and habitat procedures. Clearer focus doesn't prove swelling has resolved. LBNP, thigh cuffs, supplements, and acetazolamide are research or clinician-only options, not automatic SANS treatments.

**Step 7 — Final: Follow-up**

Stick with the clinician's follow-up plan. No drug has established SANS rescue efficacy. Don't start medicines, pressure manipulation, or invasive eye procedures based on this app.

---

## 6. SANS PROTOCOL — EMERGENCY

**Step 1 — Stop activities**

Stop risky tasks and EVA now. Alert the crew medical officer immediately. Record symptom onset and affected eye; don't wait for OCT.

**Step 2 — Local medical assessment**

Activate the on-board medical lead for immediate ocular and neurological assessment. Don't assume every acute visual problem is SANS; the clinician decides care and restrictions.

**Step 3 — Request assistance**

Get help now: request immediate assistance from the crew medical officer. Don't continue the risky task.

**Step 4 — Check whether Earth support is required**

Has the local clinician requested Earth support while care continues here?

**Step 5 — Contact Earth from Mars**

Transmit the requested case summary to Earth; continue local care under the pre-authorized protocol. Don't delay local assessment for communication.

**Step 6 — Contact Earth from other environments**

Send the requested case summary to the flight surgeons while local medical care continues. This app doesn't send messages or authorize transfer.

**Step 7 — Confirm clinical handover**

Confirm a clinician has reviewed this episode and accepted responsibility for ongoing care. Only then select Done; otherwise keep this task active and stay assisted.

**Step 8 — Final: Care transferred**

Clinical review and accepted handover are recorded. Continue medical restrictions and follow-up. This isn't a cure or EVA clearance; transfer is a clinical and mission decision.

---

## 7. MUSCLE ATROPHY PROTOCOL — MONITORING AND FOLLOW-UP

**Step 1 — Check for warning signs**

Safety check: any sudden or rapidly worsening weakness, new inability to move safely or complete egress, new intense muscle pain, breathing difficulty, or loss of consciousness? Breathing difficulty or unconsciousness is a general emergency, not proof of atrophy.

**Step 2 — Check limitations**

Is this worsening unexpected, or is it stopping you from completing a task?

**Step 3 — Notify the crew medical officer**

Tell the crew medical officer. Together, review symptoms, any pain, actual exercise load, and strength trend.

**Step 4 — Request priority medical review**

Ask the crew medical officer for priority review of the concerning finding or unexpected task limitation. A concerning number alone doesn't establish medical urgency.

**Step 5 — Review exercise and nutrition**

Review resistive and aerobic load, technique, and recovery with your exercise specialist—don't increase load yourself. Review energy and protein intake against the approved nutrition plan.

**Step 6 — Final: Follow-up**

Keep logging symptoms and training daily; repeat comparable strength tests as directed and follow prescribed rehabilitation after return. Don't train through pain, add catch-up overload, or start supplements or medicines without medical advice.

---

## 8. MUSCLE ATROPHY PROTOCOL — EMERGENCY

**Step 1 — Stop activities**

Stop exercise and risky tasks now. Get to a safe position and alert the crew medical officer immediately. Don't repeat maximal tests or wait for another sensor reading.

**Step 2 — Local medical assessment**

Activate the on-board medical lead for immediate assessment and stabilization. Investigate injury or another acute cause. Follow the local emergency protocol; don't wait for Earth.

**Step 3 — Request assistance**

Get help now: request immediate assistance from the crew medical officer. Don't continue the risky task.

**Step 4 — Check whether Earth support is required**

Has the local clinician requested Earth support while care continues here?

**Step 5 — Contact Earth from ISS**

Send the clinician-requested summary to the flight surgeons while local care continues. If care is insufficient, return decisions belong to the medical and mission team.

**Step 6 — Contact Earth from the Moon**

Send the clinician-requested summary to the flight surgeons while care continues in the habitat. Transfer depends on the vehicle, resources, and clinical decision.

**Step 7 — Contact Earth from Mars**

Transmit the requested case summary to Earth and follow the pre-authorized local protocol. Don't wait for an immediate Earth reply.

**Step 8 — Confirm clinical handover**

Confirm a clinician has reviewed this episode and accepted responsibility for ongoing care. Only then select Done; otherwise keep this task active and stay assisted.

**Step 9 — Final: Care transferred**

Clinical review and accepted handover are recorded. Follow medical restrictions and diagnosis-specific rehabilitation. Return or transfer depends on clinical need, vehicle, and resources—not a sensor value alone.