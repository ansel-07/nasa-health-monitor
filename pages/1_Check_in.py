# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: Check-in implementation generated with Codex; human review pending.
"""Check-in: measurement form, trigger alert and confirmation step. Owner: Juan Carlos.

Mascot: large at the top; small in a column next to the chart when a chart is shown
(AGENTS.md, section 8). Chart: core.charts.indicator_chart(..., compact=True).
"""
from datetime import datetime, timedelta
from math import ceil, isfinite

import streamlit as st

from core import charts, config, data, episodes, mascot, mission, triggers


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
    message, mood = "Choose an indicator and record a new measurement.", "neutral"
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

    confirmation = opened is not None and opened["status"] == "pending_confirmation"
    if confirmation:
        indicator_id = opened["trigger"]["indicator"]
        st.subheader("Repeat measurement")
        name = indicators[indicator_id]["name"]
        st.write(f"Indicator: {'Unavailable indicator' if _unfinished(name) else name}")
    else:
        indicator_id = st.selectbox(
            "Indicator", list(indicators),
            format_func=lambda key: ("Unavailable indicator" if _unfinished(indicators[key]["name"])
                                     else indicators[key]["name"]),
            key=f"check_in_indicator:{astronaut}:{environment}",
        )
    indicator = indicators[indicator_id]
    assessment_environment = opened["environment"] if confirmation else environment
    issues = [] if blocked else triggers.assessment_issues(problems, astronaut, indicator_id, assessment_environment)
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
    if any(_unfinished(indicator.get(key)) for key in ("name", "unit", "how_to_measure", "why_it_matters")):
        message, mood = "Measurement guidance is not available yet. This indicator cannot be submitted.", "serious"
    chart_col, mascot_col = st.columns([4, 1])
    with chart_col:
        st.plotly_chart(charts.indicator_chart(
            astronaut, indicator_id, compact=True, environment=environment,
        ))
    with mascot_col:
        mascot.say(message, mood, size="small")

    if opened:
        label = "Problem state" if "symptoms" in problems[opened["problem"]] else "Alert severity"
        st.write(f"{label}: {opened['severity']}")
        if opened.get("symptoms"):
            with st.expander("Symptoms at last detection"):
                symptom_config = problems[opened["problem"]].get("symptoms", {})
                st.dataframe([{"Symptom": symptom_config.get(sid, {}).get("name", sid), "Level": level}
                              for sid, level in opened["symptoms"].items()], hide_index=True)
        if opened["environment"] != environment:
            st.info("This episode keeps the mission environment in which it was opened.")
    if opened and opened["status"] == "active":
        if st.button("Open Protocol"):
            st.switch_page("pages/2_Protocol.py")

    guidance_ready = _guidance(indicator)
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
                if st.button("Simulate wait", disabled=blocked):
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
    form_id = f"check_in_form:{astronaut}:{environment}:{opened['id'] if confirmation else 'manual'}:{indicator_id}:{version}"
    with st.form(form_id, clear_on_submit=True):
        value = st.number_input(
            f"{'Repeat value' if confirmation else 'Value'} "
            f"({'unit unavailable' if _unfinished(indicator.get('unit')) else indicator['unit']})", value=None,
            placeholder="Enter your measured value", disabled=blocked or not guidance_ready or not ready,
        )
        submitted = st.form_submit_button(
            "Confirm repeat measurement" if confirmation else "Record measurement",
            disabled=blocked or not guidance_ready or not ready,
        )
    if submitted:
        if value is None or not isfinite(value):
            report("error", "Enter a finite measured value before submitting.")
        try:
            m = _measurement(astronaut, indicator_id, indicator["unit"], value)
            if confirmation:
                result = episodes.confirm(opened["id"], m)
                text = ("Repeat measurement recorded. The alert is confirmed; open Protocol to continue."
                        if result["status"] == "active" else "Repeat measurement recorded. The alert was not confirmed and has been dismissed.")
            else:
                result = episodes.on_new_measurement(m, environment)
                text = ("Measurement recorded. No alert was opened." if result is None
                        else "Measurement recorded. Review the open alert and its next step on this page.")
            issues = triggers.assessment_issues(problems, astronaut, indicator_id, assessment_environment)
            if issues:
                text = "Measurement recorded. Assessment is incomplete; see the warnings below."
        except (ValueError, KeyError, OSError) as error:
            report("error", str(error))
        st.session_state[version_key] = version + 1
        report("warning" if issues else "success", text)

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
            if st.button("Review next alert", disabled=blocked or not next_ready):
                try:
                    result = episodes.accept_pending(astronaut, environment)
                except (ValueError, KeyError, OSError) as error:
                    report("error", str(error))
                report("info", "The next alert is ready for a repeat measurement after its confirmation wait."
                       if result is not None else "There are no waiting alerts to review.")


main()
