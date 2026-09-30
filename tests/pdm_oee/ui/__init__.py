"""Tests for the command center: pure presenters, and the real page run headless with injected services and files.

No server is started and no language model is contacted; the model is scripted.
Outbox, replay, and model report live in pytest's temporary directories.
"""
