"""HTTP endpoints of the copilot API, one router per resource.

Routers parse the request, call a service, and return JSON; no business rules live here.
They reach the services through the dependencies module, so tests can inject their own.
"""
