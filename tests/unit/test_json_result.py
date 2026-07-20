import json
from datetime import date, datetime
from decimal import Decimal

from db_context.schema.formatter import MAX_CELL_WIDTH
from db_context.schema.json_result import (
    format_sql_query_result_json,
    query_result_to_jsonable,
    serialize_cell,
)


def test_serialize_null_and_string_null_differ():
    assert serialize_cell(None) == (None, False)
    assert serialize_cell("NULL") == ("NULL", False)
    assert serialize_cell("") == ("", False)


def test_serialize_datetime_decimal_truncation():
    dt = datetime(2026, 7, 20, 12, 30, 0, 123456)
    val, trunc = serialize_cell(dt)
    assert val == "2026-07-20 12:30:00.123456"
    assert trunc is False

    d, _ = serialize_cell(date(2026, 1, 2))
    assert d == "2026-01-02"

    dec, _ = serialize_cell(Decimal("10.50"))
    assert dec == "10.50"

    long = "Z" * (MAX_CELL_WIDTH + 10)
    s, trunc = serialize_cell(long)
    assert trunc is True
    assert s.endswith("…")
    assert len(s) == MAX_CELL_WIDTH


def test_query_result_json_null_vs_empty():
    result = {
        "columns": ["ID", "NAME", "STREET"],
        "rows": [
            {"ID": 1, "NAME": "A", "STREET": None},
            {"ID": 2, "NAME": "B", "STREET": ""},
            {"ID": 3, "NAME": "C", "STREET": "NULL"},
        ],
        "row_count": 3,
    }
    payload = query_result_to_jsonable(result, max_rows=100)
    assert payload["format"] == "json"
    assert payload["columns"] == ["ID", "NAME", "STREET"]
    assert payload["rows"][0][2] is None
    assert payload["rows"][1][2] == ""
    assert payload["rows"][2][2] == "NULL"
    assert payload["row_count"] == 3
    assert payload["truncated_rows"] is False

    text = format_sql_query_result_json(result, max_rows=100)
    parsed = json.loads(text)
    assert parsed["rows"][0][2] is None
    assert '"STREET"' in text or "STREET" in parsed["columns"]


def test_truncated_rows_flag_when_full_page():
    result = {
        "columns": ["ID"],
        "rows": [{"ID": i} for i in range(5)],
        "row_count": 5,
    }
    payload = query_result_to_jsonable(result, max_rows=5)
    assert payload["truncated_rows"] is True
    payload2 = query_result_to_jsonable(result, max_rows=10)
    assert payload2["truncated_rows"] is False
