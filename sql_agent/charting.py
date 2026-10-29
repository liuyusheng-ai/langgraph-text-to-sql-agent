"""Convert tabular query results into a compact Plotly-compatible spec."""

from __future__ import annotations

from numbers import Number
from typing import Any


def build_chart_spec(
    columns: list[str], rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    if len(columns) < 2 or not rows:
        return None

    dimension = columns[0]
    numeric_candidates = [
        column
        for column in columns[1:]
        if all(isinstance(row.get(column), Number) for row in rows)
    ]
    if not numeric_candidates:
        return None

    measure = numeric_candidates[-1]
    return {
        "data": [
            {
                "type": "bar",
                "x": [row.get(dimension) for row in rows],
                "y": [row.get(measure) for row in rows],
                "name": measure,
            }
        ],
        "layout": {
            "title": f"{measure} by {dimension}",
            "xaxis": {"title": dimension},
            "yaxis": {"title": measure},
        },
    }

