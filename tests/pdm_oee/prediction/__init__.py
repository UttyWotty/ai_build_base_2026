"""Tests for failure prediction: event-level alert scoring, no look-ahead, labels and eligibility, and the backtest.

Scoring rules are tested on hand-built rows; data rules on the small synthetic plant.
The small-plant backtest uses a compressed time split so every block has data.
"""
