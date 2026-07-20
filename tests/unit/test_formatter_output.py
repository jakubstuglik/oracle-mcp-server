from db_context.schema.formatter import format_sql_query_result, MAX_CELL_WIDTH


def test_format_sql_query_result_basic_table():
    """Visual/structural snapshot-style test for simple table formatting.

    Ensures:
    - Column padding is applied (NAME column wider than header)
    - Separator uses at least 3 dashes / matches computed widths
    - No truncation note for small values
    - Exact layout is stable (acts as a lightweight snapshot)
    """
    result = {
        "columns": ["ID", "NAME"],
        "rows": [
            {"ID": 1, "NAME": "ALPHA"},
            {"ID": 2, "NAME": "BETA"},
        ],
    }

    table = format_sql_query_result(result)
    expected = "\n".join([
        "| ID | NAME  |",   # NAME padded to width 5
        "| --- | ----- |",  # dashes reflect widths (>=3 rule)
        "| 1  | ALPHA |",   # ID padded to width 2; NAME exact
        "| 2  | BETA  |",   # NAME padded with trailing space
    ])

    assert table == expected, f"Unexpected table formatting:\n{table}"
    assert "Note: Some values truncated" not in table


def test_format_sql_query_result_truncation_and_note():
    """Verify truncation ellipsis and note line appear when cell exceeds MAX_CELL_WIDTH."""
    long_val = "Z" * (MAX_CELL_WIDTH + 25)
    result = {
        "columns": ["COL"],
        "rows": [{"COL": long_val}],
    }
    table = format_sql_query_result(result)

    lines = table.splitlines()
    # Header + separator + data (+ optional note line appended separately if truncation)
    assert lines[0].startswith("| COL")
    assert lines[1].startswith("| ---")
    assert "…" in lines[2], "Truncated ellipsis missing in data row"
    assert any(line.startswith("Note: Some values truncated") for line in lines[3:]), "Truncation note missing"


def test_format_sql_query_result_null_cells():
    """SQL NULL (Python None) must not crash unpacking and must render as NULL token."""
    result = {
        "columns": ["ID", "NAME", "STREET"],
        "rows": [
            {"ID": 1, "NAME": "ALPHA", "STREET": None},
            {"ID": 2, "NAME": None, "STREET": ""},
        ],
    }

    table = format_sql_query_result(result)

    assert "not enough values to unpack" not in table
    lines = table.splitlines()
    assert lines[0].startswith("| ID")
    assert "NULL" in lines[2], f"Expected NULL token for SQL null street:\n{table}"
    assert "NULL" in lines[3], f"Expected NULL token for SQL null name:\n{table}"
    # Empty string is distinct from SQL NULL
    assert "| 2" in lines[3]
    assert "ALPHA" in lines[2]
