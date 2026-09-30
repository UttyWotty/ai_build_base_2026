"""Tests for alerts and work orders: deadline, slot, priority, and dedup rules, the lift arithmetic, the outbox, and the replay.

Rules and arithmetic are tested on hand-built inputs; the replay on the small plant with the compressed split.
Nothing here writes outside pytest's temporary directories.
"""
