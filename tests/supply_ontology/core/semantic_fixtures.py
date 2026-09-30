"""Builders for small, valid raw ontology and metric documents used across the core tests.

Each builder returns a fresh nested dict, so tests can mutate one field to provoke a single failure.
The fixture ontology is a three-entity chain: order_line -> order -> customer.
"""
from __future__ import annotations

from typing import Any

RawDocument = dict[str, Any]


def raw_ontology() -> RawDocument:
    """A valid ontology: order_line many-to-one order, order many-to-one customer."""
    return {
        "entities": {
            "customer": {
                "label": "Customer",
                "description": "Buyer.",
                "key": ["customer_id"],
                "attributes": {
                    "customer_id": {"type": "string", "description": "Id."},
                    "region": {"type": "string", "description": "Region."},
                    "country": {"type": "string", "description": "Country."},
                },
            },
            "order": {
                "label": "Order",
                "description": "Header.",
                "key": ["order_id"],
                "attributes": {
                    "order_id": {"type": "string", "description": "Id."},
                    "customer_id": {"type": "string", "description": "Buyer."},
                },
            },
            "order_line": {
                "label": "Order line",
                "description": "Line.",
                "key": ["line_id"],
                "attributes": {
                    "line_id": {"type": "string", "description": "Id."},
                    "order_id": {"type": "string", "description": "Header."},
                    "qty": {"type": "integer", "description": "Quantity."},
                    "due_date": {"type": "date", "description": "Due."},
                    "status": {"type": "string", "description": "Status."},
                    "is_on_time": {"type": "boolean", "derived": True, "description": "On time."},
                },
            },
        },
        "relationships": [
            {"name": "line_order", "from": "order_line", "to": "order",
             "cardinality": "many_to_one", "join": {"order_id": "order_id"}},
            {"name": "order_customer", "from": "order", "to": "customer",
             "cardinality": "many_to_one", "join": {"customer_id": "customer_id"}},
        ],
        "hierarchies": [
            {"name": "geography", "entity": "customer", "levels": ["region", "country", "customer_id"]},
        ],
    }


def raw_metric(metric_id: str = "on_time") -> RawDocument:
    """A valid ratio metric over order_line; the id parameter lets tests build several metrics."""
    return {
        "id": metric_id,
        "label": f"Label {metric_id}",
        "description": "Share of lines on time.",
        "owner": "planning",
        "type": "ratio",
        "grain": "order_line",
        "time_dimension": "due_date",
        "numerator": {"aggregation": "count_if", "attribute": "is_on_time"},
        "denominator": {"aggregation": "count"},
        "filters": [{"attribute": "status", "operator": "not_equals", "value": "cancelled"}],
        "format": "percent",
        "synonyms": [f"synonym {metric_id}"],
    }
