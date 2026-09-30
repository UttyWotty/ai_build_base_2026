"""Streamlit user interface for asking governed questions, replaying the consistency demo, and browsing the catalog.

The UI sits above the services layer and never reaches adapters directly.
Views render service results; pure formatting lives in presenters so it can be tested without Streamlit.
"""
