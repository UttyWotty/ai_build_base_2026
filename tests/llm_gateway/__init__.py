"""Tests for the shared language model gateway.

They cover provider resolution, message conversion, the retry policy, and both adapters' request handling.
No test sends a network request; the Gemini adapter runs against an in-memory fake of the SDK client.
"""
