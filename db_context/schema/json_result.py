"""Serialize SQL query results to JSON-friendly structures for agents.

Preserves SQL NULL as JSON null (unlike markdown tables, which use a NULL token).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Sequence

from db_context.schema.formatter import MAX_CELL_WIDTH

__all__ = [
    "format_sql_query_result_json",
    "query_result_to_jsonable",
    "serialize_cell",
]


def serialize_cell(value: Any, *, max_cell_width: int = MAX_CELL_WIDTH) -> tuple[Any, bool]:
    """Convert one cell to a JSON-serializable value.

    Returns (jsonable_value, was_truncated).
    """
    if value is None:
        return None, False

    truncated = False

    if isinstance(value, bool):
        return value, False
    if isinstance(value, int) and not isinstance(value, bool):
        return value, False
    if isinstance(value, float):
        return value, False
    if isinstance(value, Decimal):
        # String keeps precision; agents can cast if needed.
        return str(value), False
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="microseconds"), False
    if isinstance(value, date):
        return value.isoformat(), False
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        # Avoid huge binary dumps in model context.
        text = raw[:max_cell_width].hex()
        if len(raw) > max_cell_width:
            truncated = True
            text = text + "…"
        return {"_type": "bytes", "hex": text, "byte_length": len(raw)}, truncated

    s = str(value)
    if len(s) > max_cell_width:
        s = s[: max_cell_width - 1] + "…"
        truncated = True
    return s, truncated


def query_result_to_jsonable(
    result: Mapping[str, Any],
    *,
    max_rows: int | None = None,
    max_cell_width: int = MAX_CELL_WIDTH,
) -> Dict[str, Any]:
    """Build a JSON-serializable dict from execute_sql_query output.

    Row shape: arrays aligned with ``columns`` (stable order, compact).
    """
    columns: List[str] = [str(c) for c in (result.get("columns") or [])]
    raw_rows: Sequence[Any] = result.get("rows") or []
    max_rows_limit = max_rows if max_rows is not None else result.get("row_count")
    if max_rows_limit is None:
        max_rows_limit = len(raw_rows)

    out_rows: List[List[Any]] = []
    truncated_cells = False

    for row in raw_rows:
        if isinstance(row, Mapping):
            cells = []
            for col in columns:
                cell, was_trunc = serialize_cell(row.get(col), max_cell_width=max_cell_width)
                if was_trunc:
                    truncated_cells = True
                cells.append(cell)
            out_rows.append(cells)
        elif isinstance(row, (list, tuple)):
            cells = []
            for val in row:
                cell, was_trunc = serialize_cell(val, max_cell_width=max_cell_width)
                if was_trunc:
                    truncated_cells = True
                cells.append(cell)
            out_rows.append(cells)
        else:
            cell, was_trunc = serialize_cell(row, max_cell_width=max_cell_width)
            if was_trunc:
                truncated_cells = True
            out_rows.append([cell])

    row_count = len(out_rows)
    # Connector already applied max_rows; if we got exactly max_rows, more may exist.
    truncated_rows = bool(max_rows is not None and row_count >= max_rows)

    payload: Dict[str, Any] = {
        "format": "json",
        "columns": columns,
        "rows": out_rows,
        "row_count": row_count,
        "max_rows": max_rows if max_rows is not None else row_count,
        "truncated_rows": truncated_rows,
        "truncated_cells": truncated_cells,
    }

    if "message" in result and result["message"]:
        payload["message"] = str(result["message"])

    return payload


def format_sql_query_result_json(
    result: Mapping[str, Any],
    *,
    max_rows: int | None = None,
    max_cell_width: int = MAX_CELL_WIDTH,
) -> str:
    """Serialize query result as a JSON text string (UTF-8, ensure_ascii=False)."""
    payload = query_result_to_jsonable(
        result, max_rows=max_rows, max_cell_width=max_cell_width
    )
    return json.dumps(payload, ensure_ascii=False, default=str)
