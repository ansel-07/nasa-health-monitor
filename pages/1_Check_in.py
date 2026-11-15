# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: Check-in implementation generated with Codex and reviewed by Juan Carlos.
"""Check-in: measurement form, trigger alert and confirmation step. Owner: Juan Carlos.

Mascot: a compact assistant line without a visual; small to the left of the chart.
Forms and buttons stay below both (AGENTS.md, section 8).
"""
from datetime import datetime, timedelta
from math import ceil, isfinite

import streamlit as st

from core import activity, charts, config, data, episodes, mascot, mission, triggers, ui


def _unfinished(value) -> bool:
    if isinstance(value, str):
        return not value.strip() or value.startswith("TODO")
    if isinstance(value, dict):
        return any(_unfinished(item) for item in value.values())
    if isinstance(value, list):
        return any(_unfinished(item) for item in value)
    return value is None


def _guidance(indicator: dict) -> bool:
    required = ("name", "unit", "how_to_measure", "why_it_matters")
    if any(_unfinished(indicator.get(key)) for key in required):
        st.warning("Measurement guidance is not available yet. Check-in cannot submit this indicator.")
        return False
    st.write(indicator["how_to_measure"])
    with st.expander("Why this measurement matters"):
        st.write(indicator["why_it_matters"])
    return True


def _measurement(astronaut: str, indicator: str, unit: str, value: float) -> dict:
    return {"timestamp": mission.now().isoformat(), "astronaut": astronaut,
            "indicator": indicator, "value": value, "unit": unit,
            "phase": "mission", "source": "manual"}


def _subjective_issues(astronaut: str, source: str, report, definitions: dict, active: list | None) -> None:
    title = "Subjective issues" if source == "check_in_list" else "Report another issue (optional)"
    with st.expander(title):
        if active is None:
            st.caption("Subjective-issue reporting is unavailable until the history can be loaded.")
            return
        if not definitions:
            st.info("Subjective issues are not configured yet.")
            return
        if any(_unfinished(item.get("label")) for item in definitions.values()):
            st.warning("Subjective-issue labels are unfinished. Reporting is unavailable.")
            return
        previous = {item["issue"] for item in active}
        st.caption("Select issues present today. To mark one as resolved, deselect it and save. "
                   "Routine issues make the linked check-in reminders run down faster; alerts come "
                   "from measurements. Urgent symptoms need action at once.")
        for item in active:
            state = "persistent" if item["persistent"] else "active"
            st.caption(f"{definitions[item['issue']]['label']}: {state}, since {item['since']}.")
        version_key = f"check_in_issues_version:{astronaut}"
        version = st.session_state.get(version_key, 0)
        routine = [key for key, item in definitions.items() if not item.get("alarm")]
        alarms = [key for key, item in definitions.items() if item.get("alarm")]
        with st.form(f"{source}:issues:{astronaut}:{version}"):
            picked = st.multiselect("Issues you are experiencing", routine,
                                    default=[key for key in routine if key in previous],
                                    format_func=lambda key: definitions[key]["label"],
                                    help="\n\n".join(f"**{definitions[k]['label']}**: {definitions[k].get('question', '')}"
                                                       for k in routine))
            picked_alarms = []
            if alarms:
                st.markdown("**Urgent symptoms** — report them at once; they need medical attention now.")
                picked_alarms = st.multiselect("Urgent symptoms you have now", alarms,
                                               default=[key for key in alarms if key in previous],
                                               format_func=lambda key: definitions[key]["label"],
                                               help="\n\n".join(f"**{definitions[k]['label']}**: {definitions[k].get('question', '')}"
                                                                  for k in alarms))
            saved = st.form_submit_button("Save issues", width="stretch")
        selected = picked + picked_alarms
        if saved:
            urgent = [definitions[key] for key in picked_alarms]
            urgent_text = (" ".join(
                    f"Urgent symptom: {item['label']}. Act now: {item['action']}" for item in urgent)) if urgent else ""
            try:
                if selected:
                    activity.report_issues(astronaut, selected, source=source)
                for issue_id in previous - set(selected):
                    activity.resolve_issue(astronaut, issue_id)
            except (ValueError, KeyError, OSError) as error:
                report("error", (urgent_text + " " if urgent_text else "")
                       + f"Some issue changes didn't save. Check your selection and retry. {error}")
            st.session_state[version_key] = version + 1
            if urgent:
                # docs/sintomas_subjetivos_atrofia_SANS.md section 3: an alarm prevails; act now.
                report("error", urgent_text)
            report("success", "Subjective issues updated." if previous or selected else "No subjective issues selected.")
        if active:
            _issue_details(astronaut, source, active, definitions, report)


# Labels for the optional details of docs/sintomas_subjetivos_atrofia_SANS.md section 4 (Edu).
_DETAIL_LABELS = {
    "sudden": "Sudden", "gradual": "Gradual",
    "improving": "Improving", "stable": "Stable", "worsening": "Worsening",
    "none": "No effect", "no_task_change": "Noticed, tasks unchanged",
    "task_adapted": "Had to adapt a task", "task_not_completed": "Could not complete a task",
    "right_eye": "Right eye", "left_eye": "Left eye", "both_eyes": "Both eyes", "not_identified": "Not identified",
}


def _issue_details(astronaut: str, source: str, active: list, definitions: dict, report) -> None:
    """Optional details of an issue reported today; the latest save of the day wins."""
    st.markdown("**Details (optional)**: describe an issue you reported, so the crew medical officer has the context.")
    ids = [item["issue"] for item in active]
    issue_id = st.selectbox("Issue", ids, format_func=lambda key: definitions[key]["label"],
                            key=f"{source}:details_issue:{astronaut}")
    saved = next((item.get("details") or {} for item in active if item["issue"] == issue_id), {})
    choices = activity.ISSUE_DETAIL_CHOICES

    def pick(label, key, options):
        value = saved.get(key)
        return st.radio(label, options, index=options.index(value) if value in options else None,
                        format_func=_DETAIL_LABELS.get, horizontal=True, key=f"{form_key}:{key}")

    form_key = f"{source}:details:{astronaut}:{issue_id}"
    with st.form(form_key):
        onset = pick("How it began", "onset", choices["onset"])
        trend = pick("Trend", "trend", choices["trend"])
        if issue_id.startswith("VIS_"):
            location = pick("Location", "location", activity.EYE_LOCATIONS)
        else:
            location = st.text_input("Location (muscle and side)", value=saved.get("location", ""),
                                     key=f"{form_key}:location")
        impact = pick("Effect on your tasks", "impact", choices["impact"])
        intensity = st.number_input("Intensity 0-10 (optional)", min_value=0, max_value=10, step=1,
                                    value=saved.get("intensity"), key=f"{form_key}:intensity",
                                    help="Your own rating. It is not a physiological measurement or an urgency threshold.")
        context = st.text_input("Context", value=saved.get("context", ""), key=f"{form_key}:context",
                                placeholder="Exercise, rest, suit, glasses, lighting, mission phase, gravity")
        notes = st.text_area("Notes", value=saved.get("notes", ""), key=f"{form_key}:notes",
                             placeholder="In your own words")
        submitted = st.form_submit_button("Save details", width="stretch")
    if submitted:
        details = {"onset": onset, "trend": trend, "location": location, "impact": impact,
                   "intensity": intensity, "context": context, "notes": notes}
        # docs/sintomas_subjetivos_atrofia_SANS.md section 4, triage rule 3.
        safety_text = ("A critical task you could not complete needs an immediate safety assessment, "
                       "even if the intensity is low.") if activity.needs_safety_assessment(details) else ""
        try:
            activity.add_issue_details(astronaut, issue_id, details)
        except (ValueError, KeyError, OSError) as error:
            report("error", (safety_text + " " if safety_text else "") + f"Couldn't save the details. {error}")
        if safety_text:
            report("error", safety_text)
        report("success", "Details saved.")


def main() -> None:
    mascot.voice_toggle()
    if not st.session_state.get("astronaut") or not st.session_state.get("environment"):
        text = "First, choose your astronaut and environment on Home."
        st.warning(text)
        mascot.say(text, "neutral", size="medium")
        return

    astronaut = st.session_state["astronaut"]
    environment = st.session_state["environment"]
    indicators = {key: value for key, value in config.load_indicators().items() if not key.startswith("_")}
    problems = {key: value for key, value in config.load_problems().items() if not key.startswith("_")}
    environments = config.load_environments()
    if environment not in environments or not indicators:
        st.error("The selected environment or measurement indicators are unavailable.")
        mascot.say("Sorry, Check-in isn't available with this selection.", "serious")
        return
    opened = data.get_open_episode(astronaut)
    if opened and (opened["problem"] not in problems or opened["trigger"]["indicator"] not in indicators):
        st.error("This episode can't be opened in Check-in.")
        mascot.say("This episode can't be opened in Check-in.", "serious")
        return
    now = mission.now()
    blocked = not problems or any(
        _unfinished({key: problem.get(key) for key in (
            ("name", "symptoms", "states", "confirm_wait_min")
            if "symptoms" in problem or "states" in problem else ("name", "triggers", "confirm_wait_min")
        )})
        for problem in problems.values()
    )
    if blocked:
        st.error("Check-in submissions are unavailable: problem names, detection rules or confirmation waits are unfinished.")

    feedback_key = f"check_in_feedback:{astronaut}:{environment}"
    feedback = st.session_state.pop(feedback_key, None)
    message, mood = "Let's record this check-in's measurements.", "neutral"
    if opened:
        problem_name = problems[opened["problem"]]["name"]
        if _unfinished(problem_name):
            problem_name = "The current alert"
        if opened["status"] == "pending_confirmation":
            message, mood = f"Hmm, {problem_name} needs another measurement to confirm it.", "worried"
        else:
            message, mood = "Your alert's confirmed. Open Protocol for the guided steps.", "serious"
    if blocked:
        message, mood = "The measurement setup isn't complete, so check-in submissions aren't ready yet.", "serious"
    if feedback:
        getattr(st, feedback["level"])(feedback["text"])
        if feedback["level"] == "error":
            message, mood = feedback["text"], "worried"

    def report(level: str, text: str) -> None:
        st.session_state[feedback_key] = {"level": level, "text": text}
        st.rerun()

    checkins = config.load_checkins()
    selection_key = f"check_in_selected:{astronaut}:{environment}"

    def select_for(indicator_id: str) -> None:
        st.session_state[selection_key] = next(
            (key for key, item in checkins.items() if indicator_id in item["indicators"]), None,
        )

    if selection_key not in st.session_state:
        st.session_state[selection_key] = None
        if opened and opened["status"] == "pending_confirmation":
            select_for(opened["trigger"]["indicator"])
    selected = st.session_state[selection_key]

    def waiting_alerts() -> None:
        _waiting_alerts(astronaut, environment, opened, problems, indicators, blocked, report, select_for)

    def open_protocol() -> None:
        st.session_state[selection_key] = None
        st.session_state.pop(feedback_key, None)
        st.switch_page("pages/2_Protocol.py")
        st.stop()

    definitions, active, history_error = {}, None, None
    try:
        definitions = config.load_subjective_issues().get("issues", {})
        active = [item for item in activity.active_issues(astronaut) if item["issue"] in definitions]
    except (ValueError, KeyError, OSError) as error:
        history_error = f"Subjective issues could not be loaded. {error}"
        st.error(history_error)
    alarms = [definitions[item["issue"]] for item in active or [] if definitions[item["issue"]].get("alarm")]
    # Reuse the Main Menu's approved narration; full actions come from configuration.
    alarm_text = "You've reported an urgent symptom. Stop the risky task and contact the crew medical officer now."

    def alarm_banners() -> None:
        for alarm in alarms:
            st.error(f"Urgent symptom: {alarm['label']}. {alarm['action']} "
                     "When it is no longer present, mark it as resolved in Subjective issues below.")

    if history_error and (not feedback or feedback["level"] != "error"):
        message, mood = history_error, "worried"

    if selected not in checkins:
        # The mascot says the open alert or an error that is on screen; otherwise it invites a check-in.
        speaks_message = opened or blocked or history_error or (feedback and feedback["level"] == "error")
        list_text, list_mood = (message, mood) if speaks_message else ("Pick a check-in. Let's record your measurements.", mood)
        if alarms:
            list_text, list_mood = alarm_text, "serious"
        # Compact mascot line, cards below it (docs/UI_STYLE.md).
        mascot.say(list_text, list_mood, size="medium")
        alarm_banners()
        st.caption("Bars show time since completion, not health status. You can measure at any time.")
        if not checkins:
            st.info("No check-ins are configured yet.")
        # Rows of three, so narrow screens stack the cards in the configured order.
        items = list(checkins.items())
        for index, (checkin_id, checkin) in enumerate(items):
            if index % 3 == 0:
                grid = st.columns(3)
            with grid[index % 3]:
                # One card per check-in (core/ui.py): the whole card opens it; the bar is time
                # since completion, never a health status.
                level = None if history_error else activity.bar_level(astronaut, "check_in", checkin_id)
                count = len(checkin["indicators"])
                recency = "recency unavailable" if level is None else f"recency {level}%"
                if ui.card(f"check_in_card:{checkin_id}", checkin["name"], "assignment",
                           f"{count} measurement{'s' if count != 1 else ''} · {recency}", level):
                    st.session_state[selection_key] = checkin_id
                    st.rerun()
        _subjective_issues(astronaut, "check_in_list", report, definitions, active)
        if opened and opened["status"] == "pending_confirmation":
            if st.button("Continue repeat measurement", width="stretch", type="primary"):
                select_for(opened["trigger"]["indicator"])
                st.rerun()
        elif opened and opened["status"] == "active":
            if st.button("Open Protocol", width="stretch", type="primary"):
                open_protocol()
        waiting_alerts()
        return

    if st.button("Back to check-ins", icon=":material/arrow_back:", type="tertiary"):
        st.session_state[selection_key] = None
        st.rerun()
    checkin = checkins[selected]
    st.subheader(checkin["name"])
    group = checkin["indicators"]
    if not group or any(key not in indicators for key in group):
        st.error("The indicators for this check-in are unavailable.")
        return
    draft_key = f"check_in_draft:{astronaut}:{environment}:{selected}"
    confirmation = (opened is not None and opened["status"] == "pending_confirmation"
                    and opened["trigger"]["indicator"] in group and draft_key not in st.session_state)
    if confirmation:
        repeat_id = opened["trigger"]["indicator"]
        st.subheader("Repeat measurement")
        name = indicators[repeat_id]["name"]
        st.write(f"Indicator: {'Unavailable indicator' if _unfinished(name) else name}")
    # One chart per indicator of the check-in; only the repeated one in repeat mode (4.2).
    field_ids = [opened["trigger"]["indicator"]] if confirmation else group
    assessment_environment = opened["environment"] if confirmation else environment
    issues = [] if blocked else list(dict.fromkeys(
        issue for key in field_ids
        for issue in triggers.assessment_issues(problems, astronaut, key, assessment_environment)
    ))
    if issues:
        for issue in issues:
            st.warning(issue)
        if not feedback or feedback["level"] != "error":
            message = "We're missing some assessments. See the warnings below."
            if opened:
                message = ("Let's repeat the indicated measurement to confirm the alert. Check the warnings below for incomplete assessments." if confirmation
                           else "Alert confirmed. Open Protocol to continue. Some assessments are incomplete; check the warnings below.")
            mood = "worried"
    if any(_unfinished(indicators[key].get(field)) for key in field_ids
           for field in ("name", "unit", "how_to_measure", "why_it_matters")):
        message, mood = "Measurement guidance isn't ready yet. We can't submit this check-in.", "serious"
    if alarms:
        message, mood = alarm_text, "serious"
    elif history_error and (not feedback or feedback["level"] != "error"):
        message, mood = history_error, "worried"
    with mascot.beside(message, mood):
        for key in field_ids:
            if len(field_ids) > 1:
                name = indicators[key].get("name")
                st.caption("Unavailable indicator" if _unfinished(name) else name)
            st.plotly_chart(charts.indicator_chart(
                astronaut, key, compact=True, environment=assessment_environment,
            ), key=f"check_in_chart:{key}", config={"displayModeBar": False})
            unit = indicators[key].get("unit", "")
            ui.indicator_tiles(astronaut, key, "" if _unfinished(unit) else unit, assessment_environment)

    alarm_banners()
    if opened:
        label = "Problem state" if "symptoms" in problems[opened["problem"]] else "Alert severity"
        st.write(f"{label}: {opened['severity'].replace('_', ' ').capitalize()}")
        if opened.get("symptoms"):
            with st.expander("Symptoms at last detection"):
                symptom_config = problems[opened["problem"]].get("symptoms", {})
                st.table([{"Symptom": symptom_config.get(sid, {}).get("name", sid), "Level": level}
                              for sid, level in opened["symptoms"].items()], hide_index=True)
        if opened["environment"] != environment:
            original_environment = environments.get(opened["environment"], {}).get("name")
            if _unfinished(original_environment):
                original_environment = opened["environment"]
            st.info(f"This episode keeps its original environment: {original_environment}.")
    if opened and opened["status"] == "active":
        if st.button("Open Protocol", width="stretch", type="primary"):
            open_protocol()
    elif opened and not confirmation and draft_key not in st.session_state:
        if st.button("Continue repeat measurement", width="stretch", type="primary"):
            select_for(opened["trigger"]["indicator"])
            st.rerun()

    completion_key = f"check_in_completion:{astronaut}:{environment}:{selected}"

    def finish_session() -> None:
        completion = st.session_state[completion_key]
        try:
            activity.complete(astronaut, "check_in", selected)
        except (ValueError, KeyError, OSError) as error:
            report("error", f"Measurements recorded, but completion didn't save. Try Finish check-in again. {error}")
        del st.session_state[completion_key]
        if completion["redirect"]:
            open_protocol()
        st.session_state[feedback_key] = completion
        st.rerun()

    completion_pending = completion_key in st.session_state
    if completion_pending and st.button("Finish check-in", width="stretch"):
        finish_session()
    guidance_ready = all(not _unfinished(indicators[key].get(field))
                         for key in field_ids for field in ("name", "unit", "how_to_measure", "why_it_matters"))
    ready = True
    if confirmation:
        wait = problems[opened["problem"]].get("confirm_wait_min")
        valid_wait = isinstance(wait, (int, float)) and not isinstance(wait, bool) and isfinite(wait) and wait >= 0
        if not valid_wait:
            st.error("The confirmation wait is unavailable in the problem configuration.")
            ready = False
        else:
            due = datetime.fromisoformat(opened["opened_at"]) + timedelta(minutes=wait)
            original = datetime.fromisoformat(opened["trigger"]["measured_at"])
            remaining = max(0.0, (due - now).total_seconds())
            ready = remaining == 0 and now > original
            if remaining:
                start = datetime.fromisoformat(config.load_mission()["start"])
                day = (due - start).days + 1
                minutes = ceil(remaining / 60)
                unit = "minute" if minutes == 1 else "minutes"
                st.info(f"Repeat after {due:%H:%M}, mission day {day} ({minutes} {unit} remaining).")
            elif not ready:
                st.info("Advance mission time before taking a new repeat measurement.")
            else:
                st.info("The confirmation wait is complete. Take a new measurement of the same indicator.")
            if not ready:
                hours = max(1, ceil(max(remaining, (original - now).total_seconds() + 1) / 3600))
                st.caption(f"For the demo, Simulate wait advances mission time by {hours} hour(s).")
                if st.button("Simulate wait", disabled=blocked, width="stretch"):
                    try:
                        mission.advance_and_detect(hours=hours, environment=environment)
                        if mission.now() <= now:
                            raise ValueError("The mission clock did not advance. The confirmation wait is still pending.")
                    except (ValueError, KeyError, OSError) as error:
                        text = str(error)
                        if mission.now() > now:
                            text = f"Mission time moved forward, but detection didn't finish. {error}"
                        report("error", text)
                    report("info", "Mission time advanced. Check the remaining wait before repeating the measurement.")

    version_key = f"check_in_form_version:{astronaut}:{environment}"
    version = st.session_state.get(version_key, 0)
    draft = st.session_state.get(draft_key) if not confirmation else None
    if draft:
        st.warning("Recording is incomplete. Submit again to save the remaining readings.")
    form_id = f"check_in_form:{astronaut}:{environment}:{opened['id'] if confirmation else 'manual'}:{selected}:{version}"
    with st.form(form_id, clear_on_submit=True):
        values = {}
        for key in field_ids:
            metadata = indicators[key]
            st.write(metadata["name"] if not _unfinished(metadata.get("name")) else "Unavailable indicator")
            _guidance(metadata)
            saved = next((item for item in draft["measurements"] if item["indicator"] == key), None) if draft else None
            values[key] = st.number_input(
                f"{'Repeat value' if confirmation else 'Value'} "
                f"({'unit unavailable' if _unfinished(metadata.get('unit')) else metadata['unit']})",
                value=saved["value"] if saved else None, key=f"{form_id}:{key}",
                placeholder="Enter your measured value",
                disabled=blocked or not guidance_ready or not ready or completion_pending or bool(draft),
            )
        submitted = st.form_submit_button(
            "Confirm repeat measurement" if confirmation else "Record measurement",
            disabled=blocked or not guidance_ready or not ready or completion_pending, width="stretch",
            type="primary",
        )
    if submitted:
        if any(value is None or not isfinite(value) for value in values.values()) and not draft:
            report("error", "Check each indicator: enter a finite measured value before submitting.")
        try:
            if confirmation:
                m = _measurement(astronaut, repeat_id, indicators[repeat_id]["unit"], values[repeat_id])
                result = episodes.confirm(opened["id"], m)
                text = ("Repeat measurement recorded. The alert is confirmed; open Protocol to continue."
                        if result["status"] == "active" else "Repeat measurement recorded. The alert was not confirmed and has been dismissed.")
            else:
                if not draft:
                    # Validate the whole group before saving a row or locking a retry draft.
                    draft = {"measurements": [episodes._measurement(
                        _measurement(astronaut, key, indicators[key]["unit"], value), mission.now())
                        for key, value in values.items()], "saved": 0}
                    st.session_state[draft_key] = draft
                result = opened
                while draft["saved"] < len(draft["measurements"]):
                    result = episodes.on_new_measurement(draft["measurements"][draft["saved"]], environment)
                    draft["saved"] += 1
                del st.session_state[draft_key]
                text = ("Measurement recorded. No alert was opened." if result is None
                        else "Measurement recorded. Review the open alert and its next step on this page.")
            issues = list(dict.fromkeys(issue for key in field_ids for issue in
                                        triggers.assessment_issues(problems, astronaut, key, assessment_environment)))
            if issues:
                text = "Measurement recorded. Assessment is incomplete; see the warnings below."
        except (ValueError, KeyError, OSError) as error:
            report("error", str(error))
        st.session_state[version_key] = version + 1
        awaiting_repeat = (result is not None and result["status"] == "pending_confirmation"
                           and result["trigger"]["indicator"] in group)
        if not awaiting_repeat:
            st.session_state[completion_key] = {
                "level": "warning" if issues else "success", "text": text,
                "redirect": confirmation and result["status"] == "active",
            }
            finish_session()
        report("warning" if issues else "success", text)

    waiting_alerts()
    _subjective_issues(astronaut, "check_in_detail", report, definitions, active)


def _waiting_alerts(astronaut, environment, opened, problems, indicators, blocked, report, select_for):
    pending = [item for item in episodes.get_pending(astronaut) if item["problem"] in problems]
    if pending:
        st.subheader("Waiting alerts")
        st.caption("These alerts have not been confirmed. The most severe alert is listed first.")
        st.dataframe([
            {"Problem": ("Pending alert" if _unfinished(problems[item["problem"]]["name"])
                         else problems[item["problem"]]["name"]), "Severity": item["severity"],
             "Measured at": item["measured_at"]} for item in pending
        ], hide_index=True)
        if opened is None:
            next_indicator = indicators.get(pending[0].get("indicator"), {})
            next_ready = all(not _unfinished(next_indicator.get(key))
                             for key in ("name", "unit", "how_to_measure", "why_it_matters"))
            st.caption("Reviewing the next alert starts a new confirmation wait in the selected mission environment.")
            if not next_ready:
                st.warning("Measurement guidance for the next alert is not available yet.")
            if st.button("Review next alert", disabled=blocked or not next_ready, width="stretch"):
                try:
                    result = episodes.accept_pending(astronaut, environment)
                except (ValueError, KeyError, OSError) as error:
                    report("error", str(error))
                if result is not None:
                    select_for(result["trigger"]["indicator"])
                report("info", "The next alert is ready for a repeat measurement after its confirmation wait."
                       if result is not None else "There are no waiting alerts to review.")


main()
