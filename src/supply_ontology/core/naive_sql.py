"""The naive text-to-SQL baseline: a prompt that shows the model the raw source tables, and the rule that accepts its reply.

This is the approach the governed layer replaces, reproduced honestly so the consistency demo can show why it fails.
Only a single SELECT (or WITH) statement is accepted from a reply; a failed or empty query earns one retry, as in the governed path.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from supply_ontology.core.errors import SemanticLayerError
from supply_ontology.core.model_response import THINK_PATTERN
from supply_ontology.core.prompt_builder import ChatMessage
from supply_ontology.core.vocabulary_model import Persona

ANSWER_COLUMN = "answer"
PATH_SEPARATOR = "/"
TABLE_SEPARATOR = "_"
FENCE_PATTERN = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
READ_STATEMENT_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
STATEMENT_TERMINATOR = ";"
# Text columns whose every value starts like 2026-09-27 are shown with their full range, so the model sees which dates exist.
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")
NO_VALUE_PROBLEM = "The query ran but returned no value (an empty result or a NULL answer)."

NAIVE_RULES = f"""You are a data analyst. Answer the business question by writing one DuckDB SQL query over the tables below.
Reply with the SQL in a ```sql code block and nothing else.
The query must return a single row with a numeric column named {ANSWER_COLUMN}. Express rates and shares as fractions between 0 and 1."""


class NaiveSqlError(SemanticLayerError):
    """A naive text-to-SQL reply did not contain one read-only statement."""


@dataclass(frozen=True)
class ColumnSchema:
    """One raw column as the naive prompt shows it: name, type, a few sample values, and for dates the full range."""

    name: str
    dtype: str
    samples: tuple[str, ...]
    value_range: tuple[str, str] | None


@dataclass(frozen=True)
class TableSchema:
    """One raw source table as the naive prompt shows it."""

    name: str
    row_count: int
    columns: tuple[ColumnSchema, ...]


def raw_table_name(relative_path: str) -> str:
    """Name a source export as a table: `erp/sales_order_items.parquet` becomes `erp_sales_order_items`."""
    stem = relative_path.rsplit(".", 1)[0]
    return stem.replace(PATH_SEPARATOR, TABLE_SEPARATOR)


def describe_tables(tables: Sequence[TableSchema]) -> str:
    """Render the raw schema, one table per block, with sample values for every column."""
    blocks = []
    for table in tables:
        lines = [f"TABLE {table.name} ({table.row_count} rows)"]
        lines += [_describe_column(c) for c in table.columns]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _describe_column(column: ColumnSchema) -> str:
    if column.value_range is not None:
        return f"  {column.name} {column.dtype}  from {column.value_range[0]} to {column.value_range[1]}"
    return f"  {column.name} {column.dtype}  e.g. {', '.join(column.samples)}"


def build_naive_messages(tables: Sequence[TableSchema], as_of: date, persona: Persona, question: str) -> list[ChatMessage]:
    """The naive prompt for one persona: the raw schema, today's date, and the team's framing of the question."""
    system = f"{NAIVE_RULES}\nToday is {as_of.isoformat()}.\n\n{describe_tables(tables)}"
    user = f"I work in {persona.label} ({persona.description})\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def extract_select(reply: str) -> str:
    """Return the single read-only statement in a reply, without a trailing semicolon."""
    text = THINK_PATTERN.sub("", reply)
    fenced = FENCE_PATTERN.search(text)
    sql = (fenced.group(1) if fenced else text).strip().rstrip(STATEMENT_TERMINATOR).strip()
    if not sql:
        raise NaiveSqlError("Reply contains no SQL.")
    if STATEMENT_TERMINATOR in sql:
        raise NaiveSqlError("Reply must contain exactly one SQL statement.")
    if not READ_STATEMENT_PATTERN.match(sql):
        raise NaiveSqlError("Only SELECT or WITH queries are accepted.")
    return sql


def build_naive_retry_message(problem: str) -> ChatMessage:
    """The one follow-up a naive run gets: what went wrong, and a request for a corrected query."""
    return {"role": "user", "content": f"That query did not produce an answer: {problem}\nReply with a corrected query in a ```sql code block."}
