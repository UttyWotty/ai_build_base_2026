"""Compiles a validated query spec into one parameterised SQL statement plus a stable fingerprint.

Each metric becomes a CTE; the CTEs are joined on the shared dimension and period columns, and ratios divide with NULLIF.
The same spec always yields byte-identical SQL, which is what lets the demo prove that different phrasings resolved identically.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.errors import QueryValidationError
from supply_ontology.core.query_spec import QuerySpec
from supply_ontology.core.query_validator import validate_query
from supply_ontology.core.sql_fragments import (
    CTE_PREFIX,
    DENOMINATOR_SUFFIX,
    NUMERATOR_SUFFIX,
    PERIOD_COLUMN,
    metric_cte,
)

FINGERPRINT_LENGTH = 16


@dataclass(frozen=True)
class CompiledQuery:
    """SQL text, its bound parameters, the output key columns, and a fingerprint of both."""

    sql: str
    parameters: tuple[object, ...]
    key_columns: tuple[str, ...]
    metric_columns: tuple[str, ...]
    fingerprint: str


def compile_query(spec: QuerySpec, catalog: SemanticCatalog, as_of: date) -> CompiledQuery:
    """Validate and compile against the data's as-of date; raises QueryValidationError listing every issue."""
    issues = validate_query(spec, catalog)
    if issues:
        raise QueryValidationError(tuple(issues))
    keys = [d.alias for d in spec.dimensions] + ([PERIOD_COLUMN] if spec.time_grain is not None else [])
    ctes, parameters, outputs = [], [], []
    for metric_id in spec.metrics:
        metric = catalog.metrics[metric_id]
        body = metric_cte(metric, spec, catalog, as_of)
        ctes.append(f"{CTE_PREFIX}{metric_id} AS (\n{body.sql}\n)")
        parameters.extend(body.parameters)
        numerator, denominator = f"{metric_id}{NUMERATOR_SUFFIX}", f"{metric_id}{DENOMINATOR_SUFFIX}"
        if metric.denominator is None:
            outputs += [numerator, f"{numerator} AS {metric_id}"]
        else:
            outputs += [numerator, denominator,
                        f"CAST({numerator} AS DOUBLE) / NULLIF({denominator}, 0) AS {metric_id}"]
    sql = "\n".join([
        "WITH " + ",\n".join(ctes),
        "SELECT " + ", ".join(keys + outputs),
        "FROM " + _join_ctes(spec.metrics, keys),
        *([f"ORDER BY {', '.join(keys)}"] if keys else []),
    ])
    return CompiledQuery(sql, tuple(parameters), tuple(keys), tuple(spec.metrics), _fingerprint(sql, parameters))


def _join_ctes(metric_ids: tuple[str, ...], keys: list[str]) -> str:
    names = [f"{CTE_PREFIX}{m}" for m in metric_ids]
    joiner = f" FULL OUTER JOIN {{}} USING ({', '.join(keys)})" if keys else " CROSS JOIN {}"
    return names[0] + "".join(joiner.format(name) for name in names[1:])


def _fingerprint(sql: str, parameters: list[object]) -> str:
    payload = sql + "\n" + json.dumps(parameters, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:FINGERPRINT_LENGTH]
