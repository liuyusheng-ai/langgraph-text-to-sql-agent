"""SQLAlchemy database adapter and a reproducible demo dataset."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


class AgentDatabase:
    def __init__(self, database_url: str = "sqlite:///data/analytics.db") -> None:
        if database_url.startswith("sqlite:///"):
            db_path = database_url.removeprefix("sqlite:///")
            if db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(database_url, future=True)
        self._create_history_table()

    def _create_history_table(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS query_history (
                        id INTEGER PRIMARY KEY,
                        question TEXT NOT NULL,
                        sql_text TEXT NOT NULL,
                        row_count INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
            )

    def seed_demo_data(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS sales (
                        id INTEGER PRIMARY KEY,
                        order_date TEXT NOT NULL,
                        region TEXT NOT NULL,
                        product TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        amount REAL NOT NULL
                    )
                    """
                )
            )
            count = connection.execute(text("SELECT COUNT(*) FROM sales")).scalar_one()
            if count:
                return
            rows = [
                ("2026-01-03", "华北", "Agent 工作台", 3, 4200.0),
                ("2026-01-07", "华东", "知识库服务", 5, 7500.0),
                ("2026-01-12", "华南", "数据分析助手", 2, 3600.0),
                ("2026-02-02", "华东", "Agent 工作台", 4, 5600.0),
                ("2026-02-11", "华北", "知识库服务", 6, 9000.0),
                ("2026-03-06", "华南", "Agent 工作台", 5, 7000.0),
                ("2026-03-18", "华东", "数据分析助手", 3, 5400.0),
                ("2026-04-09", "华北", "数据分析助手", 4, 7200.0),
            ]
            connection.execute(
                text(
                    """
                    INSERT INTO sales
                    (order_date, region, product, quantity, amount)
                    VALUES (:order_date, :region, :product, :quantity, :amount)
                    """
                ),
                [
                    {
                        "order_date": row[0],
                        "region": row[1],
                        "product": row[2],
                        "quantity": row[3],
                        "amount": row[4],
                    }
                    for row in rows
                ],
            )

    def schema_text(self) -> str:
        inspector = inspect(self.engine)
        sections: list[str] = []
        for table_name in inspector.get_table_names():
            if table_name == "query_history":
                continue
            columns = inspector.get_columns(table_name)
            rendered = ", ".join(
                f"{column['name']} {column['type']}" for column in columns
            )
            sections.append(f"{table_name}({rendered})")
        return "\n".join(sections)

    def execute_readonly(self, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
        with self.engine.connect() as connection:
            result = connection.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result.fetchall()]
        return columns, rows

    def record_history(
        self, question: str, sql: str, row_count: int, status: str
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO query_history
                    (question, sql_text, row_count, status, created_at)
                    VALUES (:question, :sql_text, :row_count, :status, :created_at)
                    """
                ),
                {
                    "question": question,
                    "sql_text": sql,
                    "row_count": row_count,
                    "status": status,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT id, question, sql_text, row_count, status, created_at
                    FROM query_history
                    ORDER BY id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    def json_rows(rows: list[dict[str, Any]]) -> str:
        return json.dumps(rows, ensure_ascii=False, default=str)

