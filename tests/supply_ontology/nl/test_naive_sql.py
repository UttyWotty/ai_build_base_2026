"""Pure rules of the naive text-to-SQL baseline and the demo's agreement rule.

Replies are accepted only as one read-only statement, with thinking blocks and code fences stripped.
The prompt must show every raw table, today's date, and the persona's framing.
"""
from __future__ import annotations

from datetime import date

import pytest

from supply_ontology.core.demo_script import value_spread, values_agree
from supply_ontology.core.naive_sql import (
    ColumnSchema,
    NaiveSqlError,
    TableSchema,
    build_naive_messages,
    build_naive_retry_message,
    extract_select,
    raw_table_name,
)
from tests.supply_ontology.nl.conftest import CATALOG

TABLE = TableSchema("erp_sales_order_items", 3, (ColumnSchema("STATUS", "object", ("O", "C"), None),
                                                ColumnSchema("CREATED_ON", "object", ("2024-09-30",), ("2024-09-30", "2026-09-27"))))


def test_table_names_follow_the_export_path() -> None:
    assert raw_table_name("erp/sales_order_items.parquet") == "erp_sales_order_items"
    assert raw_table_name("supplier_portal/confirmations.xlsx") == "supplier_portal_confirmations"


def test_fenced_sql_is_extracted_without_thinking_or_semicolon() -> None:
    reply = "<think>use the ERP</think>Here:\n```sql\nSELECT 0.8 AS answer;\n```"
    assert extract_select(reply) == "SELECT 0.8 AS answer"
    assert extract_select("with x as (select 1) select * from x") == "with x as (select 1) select * from x"


@pytest.mark.parametrize("reply", ["", "```sql\n```", "DELETE FROM erp_sales_order_items",
                                   "SELECT 1; DROP VIEW erp_sales_order_items", "COPY t TO 'x.csv'"])
def test_anything_but_one_read_statement_is_refused(reply: str) -> None:
    with pytest.raises(NaiveSqlError):
        extract_select(reply)


def test_prompt_shows_schema_date_and_persona() -> None:
    persona = CATALOG.vocabulary.personas["planning"]
    system, user = build_naive_messages([TABLE], date(2026, 9, 27), persona, "What was our service level?")
    assert "TABLE erp_sales_order_items (3 rows)" in system["content"] and "e.g. O, C" in system["content"]
    assert "2026-09-27" in system["content"]
    assert "CREATED_ON object  from 2024-09-30 to 2026-09-27" in system["content"]
    assert persona.label in user["content"] and user["content"].endswith("What was our service level?")


def test_values_agree_only_when_all_present_and_close() -> None:
    assert values_agree([0.78, 0.7801, 0.7799])
    assert not values_agree([0.78, 0.61])
    assert not values_agree([0.78, None])
    assert not values_agree([])
    assert value_spread([0.78, 0.61, None]) == pytest.approx(0.17)
    assert value_spread([0.78]) is None


def test_retry_message_states_the_problem_and_asks_for_sql() -> None:
    message = build_naive_retry_message("Binder Error: table so not found")
    assert message["role"] == "user" and "Binder Error" in message["content"] and "```sql" in message["content"]
