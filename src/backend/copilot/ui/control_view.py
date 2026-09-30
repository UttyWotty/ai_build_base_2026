"""The control room: open alerts at the demo clock, and for the selected one its full impact and the copilot's plan.

It shows the spare position across sites, the supplier's governed record, every recovery option priced, the sensor
evidence, and the customer lines at risk; one button asks the agent to draft the plan for approval.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from copilot.ui import presenters as p
from copilot.ui.resources import history, run_agent, tools
from copilot.ui.trace_view import render_run

CHART_HEIGHT = 220


def render_control_room() -> None:
    toolbox = tools()
    alerts = toolbox.list_open_alerts()["alerts"]
    if not alerts:
        st.info("No alerts are waiting for a repair at this time.")
        return
    impacts = {a["alert_id"]: toolbox.analyse_alert_impact(a["alert_id"]) for a in alerts}
    _headline(alerts, impacts)
    choice = st.selectbox("Alert", [a["alert_id"] for a in alerts], key="alert-choice",
                          format_func=lambda i: p.alert_label(next(a for a in alerts if a["alert_id"] == i)))
    _detail(choice, impacts[choice], toolbox.get_sensor_evidence(choice))


def _headline(alerts: list[dict], impacts: dict[str, dict]) -> None:
    saved_hours = sum(p.avoided(i)[0] for i in impacts.values())
    saved_cost = sum(p.avoided(i)[1] for i in impacts.values())
    conflicts = sum(1 for i in impacts.values() if p.conflict_note(i))
    cols = st.columns(4)
    cols[0].metric("Open alerts", len(alerts))
    cols[1].metric("Alerts in a spare conflict", conflicts)
    cols[2].metric("Downtime avoided by the plan", p.hours(saved_hours))
    cols[3].metric("Cost avoided by the plan", p.money(saved_cost))


def _detail(alert_id: str, impact: dict, evidence: dict) -> None:
    note = p.conflict_note(impact)
    if note:
        st.warning(note)
    best = p.recommended(impact)
    left, middle, right = st.columns(3)
    with left:
        _spare_card(impact)
    with middle:
        _supplier_card(impact)
    with right:
        st.markdown("**Recommended by the rules**")
        st.metric(f"{p.option_label(best['kind'])} ({best['source']})", p.money(best["total_cost_usd"]),
                  help="Extra spend plus lost contribution")
        st.caption(f"Ready {best['ready_at']}; downtime {p.hours(best['downtime_hours'])}, "
                   f"worst case {p.hours(best['worst_case_downtime_hours'])}.")
    st.markdown("**Every way to get the spare**")
    st.dataframe(pd.DataFrame(p.option_rows(impact)), hide_index=True, width="stretch")
    _orders_at_risk(impact)
    _evidence_chart(evidence)
    if st.button("Draft the plan with the copilot", key=f"plan-{alert_id}", type="primary"):
        with st.spinner("The copilot is analysing the alert..."):
            run = run_agent(f"Prepare the action plan for alert {alert_id}. Choose the best option, explain why in two "
                            "sentences, and create the proposal.")
        history().append(run)
        render_run(run, key=f"plan-run-{alert_id}")


def _spare_card(impact: dict) -> None:
    st.markdown("**Spare**")
    spare = impact.get("spare")
    if not spare:
        st.caption("This repair needs no spare part.")
        return
    local = spare["local"]
    st.metric(f"{spare['label']} at {local['site_id']}", local["on_hand"], help=spare["spare_part_id"])
    for sister in spare["sister_sites"]:
        st.caption(f"{sister['site_id']}: {sister['on_hand']} on hand, {len(sister['alerts_queued_for_this_spare'])} queued")
    for order in local["open_orders"]:
        st.caption(f"Open order {order['po_id']}: promised {order['promised']}, expected {order['expected']}")


def _supplier_card(impact: dict) -> None:
    st.markdown("**Supplier**")
    supplier = impact.get("supplier")
    if not supplier:
        st.caption("No supplier involved.")
        return
    st.metric(f"{supplier['name']} on time", p.percent(supplier["on_time_percent"]),
              help=f"Governed metric supplier_otd, {supplier['window']}")
    st.caption(f"Expected {supplier['expected_days_late']:g} days late. SQL fingerprint {supplier['sql_fingerprint']}.")


def _orders_at_risk(impact: dict) -> None:
    base = p.baseline(impact)
    if base["orders_at_risk"]:
        st.markdown(f"**Customer lines at risk without the plan** ({p.option_label(base['kind'])}: "
                    f"{base['customer_lines_at_risk']} lines)")
        st.dataframe(pd.DataFrame(base["orders_at_risk"]), hide_index=True, width="stretch")


def _evidence_chart(evidence: dict) -> None:
    rows = pd.DataFrame(p.sensor_rows(evidence))
    if rows.empty:
        return
    st.markdown(f"**Why the model raised it:** {evidence['failure_mode']}, P-F interval {evidence['pf_interval_days']:g} days. "
                f"{evidence['recommended_action']}")
    for sensor, frame in rows.groupby("sensor", sort=False):
        band = alt.Chart(frame).mark_area(opacity=0.15).encode(x="day:T", y="normal_low:Q", y2="normal_high:Q")
        line = alt.Chart(frame).mark_line(point=True).encode(
            x=alt.X("day:T", title=None), y=alt.Y("mean:Q", title=f"{sensor} ({frame['unit'].iloc[0]})"))
        st.altair_chart((band + line).properties(height=CHART_HEIGHT), width="stretch")
