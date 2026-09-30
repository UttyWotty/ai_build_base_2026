"""The Streamlit command center: alert triage, asset health, OEE and losses, investigation, and the prediction model.

The UI sits above the services layer and never reaches adapters directly.
Views render service results; pure formatting lives in presenters so it is tested without Streamlit.
"""
