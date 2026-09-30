"""The Approvals tab: every plan the copilot proposed, waiting for a person to approve or reject it.

The numbers on each proposal come from the impact analysis, not from the model's text.
Approving records the decision only; the systems of record would take it from here.
"""
from __future__ import annotations

import streamlit as st

from copilot.ui import presenters as p
from copilot.ui.resources import services

PENDING = "pending"


def render_approvals() -> None:
    store = services().proposals
    proposals = list(reversed(store.all()))
    if not proposals:
        st.info("No proposals yet. Ask the copilot to draft a plan from the control room.")
        return
    for proposal in proposals:
        _card(store, proposal)


def _card(store, proposal: dict) -> None:
    title = (f"{proposal['status'].upper()}  {proposal['asset_id']}: {p.option_label(proposal['option_kind'])} "
             f"from {proposal['option_source']}")
    with st.expander(title, expanded=proposal["status"] == PENDING):
        cols = st.columns(4)
        cols[0].metric("Spare ready", str(proposal["ready_at"])[:16])
        cols[1].metric("Extra cost", p.money(proposal["extra_cost_usd"]))
        cols[2].metric("Downtime", p.hours(proposal["downtime_hours"]))
        cols[3].metric("Customer lines at risk", len(proposal["orders_at_risk"]))
        st.markdown(f"**Work order note:** {proposal['work_order_note'] or '-'}")
        st.markdown(f"**Customer note:** {proposal['customer_note'] or '-'}")
        st.caption(f"{proposal['proposal_id']} for {proposal['alert_id']}, drafted at {str(proposal['created_at'])[:16]}.")
        if proposal["status"] == PENDING:
            approve, reject = st.columns(2)
            if approve.button("Approve", key=f"approve-{proposal['proposal_id']}", type="primary"):
                store.set_status(proposal["proposal_id"], "approved")
                st.rerun()
            if reject.button("Reject", key=f"reject-{proposal['proposal_id']}"):
                store.set_status(proposal["proposal_id"], "rejected")
                st.rerun()
