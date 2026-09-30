"""The "How it works" tab: the sense, reason, act loop, the architecture on Google Cloud, and the guardrails.

Judges and new users read this tab to see what is real: every claim here points at something the app shows.
The diagram is Graphviz source rendered by Streamlit, so it needs no image files.
"""
from __future__ import annotations

import streamlit as st

ARCHITECTURE = """
digraph {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#f4f6fb", fontname="Helvetica", fontsize=11];
  sensors [label="Sensors, MES, CMMS\\n(plant, synthetic)"]; erp [label="ERP, TMS, suppliers\\n(supply network, synthetic)"];
  predict [label="Failure prediction\\n(gradient boosting)"]; bridge [label="Governed bridge\\nsites, spares, suppliers, lines"];
  impact [label="Impact analysis\\npoint in time"]; agent [label="Gemini agent\\nAgent Development Kit", fillcolor="#e3ecff"];
  human [label="Person approves\\nor rejects", fillcolor="#e8f5e9"];
  sensors -> predict -> impact; erp -> bridge -> impact; impact -> agent [label=" governed tools"]; agent -> human [label=" proposals"];
}
"""

LOOP = """
1. **Sense.** A failure-prediction model scores every asset from its sensor history. On the test period it caught
   27 of 41 failures, at 0.16 false alerts per asset-month and a median warning of 86 hours.
2. **Reason.** A Gemini agent built with Google's Agent Development Kit investigates with governed tools only: sensor
   evidence, spare stock at both sites, the supplier's governed on-time delivery, and the customer lines at risk.
3. **Act.** It proposes the work order, the parts action, and the customer note. A person approves or rejects each one.
"""

GUARDRAILS = """
- **No invented numbers.** Every number in an answer is checked against the tool results before it is shown as verified.
- **No SQL from the model.** Supplier metrics compile from governed definitions; the SQL fingerprint is shown.
- **No peeking at the future.** Every tool answers as of the demo clock; outcomes count only once they are in the past.
- **No silent actions.** The agent creates proposals; only a person can approve them.
"""

GOOGLE_CLOUD = """
| Concern | On Google Cloud |
|---|---|
| Reasoning | Gemini on Vertex AI, through the Agent Development Kit |
| App | Cloud Run, one container |
| Data | DuckDB in the container; BigQuery as the warehouse mode |
| Files | Cloud Storage |
"""


def render_about() -> None:
    st.markdown(LOOP)
    st.graphviz_chart(ARCHITECTURE, width="stretch")
    left, right = st.columns(2)
    with left:
        st.markdown("**Guardrails**")
        st.markdown(GUARDRAILS)
    with right:
        st.markdown("**Google Cloud**")
        st.markdown(GOOGLE_CLOUD)
    st.caption("All data is synthetic and generated from a seed; no real plant, supplier, or customer data is used.")
