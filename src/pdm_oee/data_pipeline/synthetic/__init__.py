"""Seeded synthetic plant: one consistent year of operations simulated first, then rendered as messy source exports.

Simulation modules are pure functions of the configuration and seed; only writer.py and cli.py touch the filesystem.
Truth tables exist for testing the conform pipeline and are never read by it.
"""
