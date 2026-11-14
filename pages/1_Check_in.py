# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: Check-in implementation generated with Codex; human review pending.
"""Check-in: measurement form, trigger alert and confirmation step. Owner: Juan Carlos.

Mascot: large and centered without a visual; small to the left of the chart.
Forms and buttons stay below both (AGENTS.md, section 8).
"""
from datetime import datetime, timedelta
from math import ceil, isfinite

import streamlit as st

from core import activity, charts, config, data, episodes, mascot, mission, triggers


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


def _subjective_issues(astronaut: str, source: str, report) -> None:
    title = "Subjective issues" if source == "check_in_list" else "Report another issue (optional)"
    with st.expander(title):
        definitions = config.load_subjective_issues().get("issues", {})
        if not definitions:
            st.info("Subjective issues are not configured yet.")
            return
        if any(_unfinished(item.get("label")) for item in definitions.values()):
            st.warning("Subjective-issue labels are unfinished. Reporting is unavailable.")
            return
        try:
            active = [item for item in activity.active_issues(astronaut) if item["issue"] in definitions]
        except (ValueError, KeyError, OSError) as error:
            st.error(f"Subjective issues could not be loaded. {error}")
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
            try:
                if selected:
                    activity.report_issues(astronaut, selected, source=source)
                for issue_id in previous - set(selected):
                    activity.resolve_issue(astronaut, issue_id)
            except (ValueError, KeyError, OSError) as error:
                report("error", f"Issue changes could not be fully saved. Review your selection and retry. {error}")
            st.session_state[version_key] = version + 1
            urgent = [definitions[key] for key in picked_alarms]
            if urgent:
                # docs/sintomas_subjetivos_atrofia_SANS.md section 3: an alarm prevails; act now.
                report("error", "Urgent symptom reported. " + " ".join(
                    f"{item['label']}: {item['action']}" for item in urgent))
            report("success", "Subjective issues updated." if previous or selected else "No subjective issues selected.")


def main() -> None:
    st.title("Check-in")
    mascot.voice_toggle()
    if not st.session_state.get("astronaut") or not st.session_state.get("environment"):
        text = "Choose an astronaut and environment on the Home page first."
        st.warning(text)
        mascot.say(text, "neutral", size="large")
        return

    astronaut = st.session_state["astronaut"]
    environment = st.session_state["environment"]
    indicators = {key: value for key, value in config.load_indicators().items() if not key.startswith("_")}
    problems = {key: value for key, value in config.load_problems().items() if not key.startswith("_")}
    environments = config.load_environments()
    if environment not in environments or not indicators:
        st.error("The selected environment or measurement indicators are unavailable.")
        mascot.say("Check-in is unavailable with the current selection.", "serious")
        return
    opened = data.get_open_episode(astronaut)
    if opened and (opened["problem"] not in problems or opened["trigger"]["indicator"] not in indicators):
        st.error("This episode is not available for Check-in.")
        mascot.say("This episode is not available for Check-in.", "serious")
        return
    now = mission.now()
    st.caption(f"Mission time: {now.isoformat(timespec='seconds')} | Environment: {environments[environment]['name']}")
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
    message, mood = "Record the measurements of this check-in.", "neutral"
    if opened:
        problem_name = problems[opened["problem"]]["name"]
        if _unfinished(problem_name):
            problem_name = "The current alert"
        if opened["status"] == "pending_confirmation":
            message, mood = f"{problem_name} needs a repeat measurement before it can be confirmed.", "worried"
        else:
            message, mood = "Your alert is confirmed. Open Protocol to continue with the guided steps.", "serious"
    if blocked:
        message, mood = "Check-in submissions are unavailable until the measurement configuration is complete.", "serious"
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

    if selected not in checkins:
        # Urgent subjective symptoms prevail, as in the Main Menu (AGENTS.md 5.6): they stay
        # visible until the astronaut marks them resolved below.
        definitions = config.load_subjective_issues().get("issues", {})
        try:
            alarms = [definitions[item["issue"]] for item in activity.active_issues(astronaut)
                      if definitions.get(item["issue"], {}).get("alarm")]
        except (ValueError, KeyError, OSError):
            alarms = []
        list_text, list_mood = (message, mood) if opened else ("Choose a check-in to record your measurements.", mood)
        if alarms:
            list_text, list_mood = ("You reported an urgent symptom. Stop the risky task and contact "
                                    "the crew medical officer now.", "serious")
        # Big centred mascot, cards below it (docs/FRONTEND_MASCOT_LAYOUT.md 4.1).
        mascot.say(list_text, list_mood, size="large")
        for alarm in alarms:
            st.error(f"Urgent symptom: {alarm['label']}. {alarm['action']} "
                     "When it is no longer present, mark it as resolved in Subjective issues below.")
        st.caption("Bars show time since completion, not health status. You can measure at any time.")
        if not checkins:
            st.info("No check-ins are configured yet.")
        grid = st.columns(3)
        for index, (checkin_id, checkin) in enumerate(checkins.items()):
            with grid[index % 3]:
                with st.container(border=True, key=f"check_in_activity_{index}"):
                    if st.button(checkin["name"], key=f"check_in_card:{checkin_id}", width="stretch"):
                        st.session_state[selection_key] = checkin_id
                        st.rerun()
                    level = activity.bar_level(astronaut, "check_in", checkin_id)
                    color = "#81C995" if level >= 80 else "#FDD663" if level >= 40 else "#F28B82"
                    st.html(f"<style>.st-key-check_in_activity_{index} [data-testid='stProgressBarTrack'] > div"
                            f" {{background-color: {color};}}</style>")
                    st.progress(level, text=f"Activity recency: {level}%")
        _subjective_issues(astronaut, "check_in_list", report)
        if opened and opened["status"] == "pending_confirmation":
            if st.button("Continue repeat measurement", width="stretch"):
                select_for(opened["trigger"]["indicator"])
                st.rerun()
        elif opened and opened["status"] == "active":
            if st.button("Open Protocol", width="stretch"):
                open_protocol()
        waiting_alerts()
        return

    if st.button("Back to check-ins"):
        st.session_state[selection_key] = None
        st.rerun()
    checkin = checkins[selected]
    st.header(checkin["name"])
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
            message = "Some assessments are incomplete. See the warnings below."
            if opened:
                next_step = ("Repeat the indicated measurement to confirm the alert." if confirmation
                             else "Your alert is confirmed; open Protocol to continue.")
                message = next_step + " Some assessments are incomplete; see the warnings below."
            mood = "worried"
    if any(_unfinished(indicators[key].get(field)) for key in field_ids
           for field in ("name", "unit", "how_to_measure", "why_it_matters")):
        message, mood = "Measurement guidance is not available yet. This check-in cannot be submitted.", "serious"
    with mascot.beside(message, mood):
        for key in field_ids:
            if len(field_ids) > 1:
                name = indicators[key].get("name")
                st.caption("Unavailable indicator" if _unfinished(name) else name)
            st.plotly_chart(charts.indicator_chart(
                astronaut, key, compact=True, environment=assessment_environment,
            ), key=f"check_in_chart:{key}")

    if opened:
        label = "Problem state" if "symptoms" in problems[opened["problem"]] else "Alert severity"
        st.write(f"{label}: {opened['severity']}")
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
        if st.button("Open Protocol", width="stretch"):
            open_protocol()
    elif opened and not confirmation and draft_key not in st.session_state:
        if st.button("Continue repeat measurement", width="stretch"):
            select_for(opened["trigger"]["indicator"])
            st.rerun()

    completion_key = f"check_in_completion:{astronaut}:{environment}:{selected}"

    def finish_session() -> None:
        completion = st.session_state[completion_key]
        try:
            activity.complete(astronaut, "check_in", selected)
        except (ValueError, KeyError, OSError) as error:
            report("error", f"Measurements recorded, but completion could not be saved. Use Finish check-in to retry. {error}")
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
                st.info(f"Repeat after {due.isoformat(timespec='seconds')} ({ceil(remaining / 60)} minute(s) remaining).")
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
                            text = "Mission time advanced, but detection could not finish. " + text
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
        )
    if submitted:
        if any(value is None or not isfinite(value) for value in values.values()) and not draft:
            report("error", "Enter a finite measured value for every indicator before submitting.")
        try:
            if confirmation:
                m = _measurement(astronaut, repeat_id, indicators[repeat_id]["unit"], values[repeat_id])
                result = episodes.confirm(opened["id"], m)
                text = ("Repeat measurement recorded. The alert is confirmed; open Protocol to continue."
                        if result["status"] == "active" else "Repeat measurement recorded. The alert was not confirmed and has been dismissed.")
            else:
                if not draft:
                    draft = {"measurements": [_measurement(astronaut, key, indicators[key]["unit"], value)
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
    _subjective_issues(astronaut, "check_in_detail", report)


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
