"""The alert queue: draft work orders from the outbox, most urgent first, with evidence and approve or dismiss buttons.

Approving or dismissing only changes the draft's status in the simulated outbox; nothing is sent anywhere.
The counts at the top show how much work is waiting and how urgent it is.
"""
from __future__ import annotations

import streamlit as st

from pdm_oee.services.command_center import draft_orders, update_draft
from pdm_oee.ui.presenters import draft_title, evidence_line, slot_text, sort_drafts
from pdm_oee.ui.resources import mode_labels, outbox_path

STATUS_FILTERS = ("draft", "approved", "dismissed", "all")
ALL = "all"


def render_queue() -> None:
    drafts = draft_orders(outbox_path())
    if not drafts:
        st.info("The outbox is empty. Run `make alerts` to replay the test period's alerts as draft work orders.")
        return
    waiting = [d for d in drafts if d["status"] == "draft"]
    columns = st.columns(4)
    columns[0].metric("Waiting", len(waiting))
    for column, level in zip(columns[1:], ("P1", "P2", "P3")):
        column.metric(level, sum(d["priority"] == level for d in waiting))
    status = st.radio("Show", STATUS_FILTERS, horizontal=True)
    labels = mode_labels()
    for draft in sort_drafts([d for d in drafts if status == ALL or d["status"] == status]):
        with st.expander(draft_title(draft, labels)):
            for item in draft["evidence"]:
                st.markdown(f"- {evidence_line(item)}")
            st.markdown(f"**Repair by** {draft['deadline_at']}. {slot_text(draft)}.")
            st.markdown(f"**Action:** {draft['recommended_action']}")
            if draft["status"] == "draft":
                left, right = st.columns(2)
                if left.button("Approve", key=f"approve-{draft['alert_id']}"):
                    update_draft(str(draft["alert_id"]), "approved", outbox_path())
                    st.rerun()
                if right.button("Dismiss", key=f"dismiss-{draft['alert_id']}"):
                    update_draft(str(draft["alert_id"]), "dismissed", outbox_path())
                    st.rerun()
