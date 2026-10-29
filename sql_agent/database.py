"""SQLAlchemy database adapter, read-only execution and a reproducible demo dataset."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine


class QueryTimeout(Exception):
    pass


# Chinese words a user may say for each table or column; used by schema retrieval.
SCHEMA_ALIASES = {
    "sales": "销售 销量 订单 销售额 金额 明细",
    "sales.order_date": "日期 月份 月度 趋势 时间",
    "sales.region": "地区 区域 大区",
    "sales.product": "产品 商品",
    "sales.quantity": "销量 数量 件数",
    "sales.amount": "销售额 金额 收入",
    "products": "产品 商品 类别 品类 单价 价格",
    "products.category": "类别 品类 分类",
    "products.unit_price": "单价 价格 定价",
}


class AgentDatabase:
    def __init__(self, database_url: str = "sqlite:///data/analytics.db") -> None:
        self.is_sqlite = database_url.startswith("sqlite")
        if database_url.startswith("sqlite:///"):
            db_path = database_url.removeprefix("sqlite:///")
            if db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(database_url, future=True)
        # Generated SQL runs on a second engine whose connections refuse every write.
        self.readonly_engine: Engine = create_engine(database_url, future=True)
        if self.is_sqlite:
            event.listen(self.readonly_engine, "connect", _sqlite_query_only)
        self._create_history_table()

    def _create_history_table(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text(
                """
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY,
                    question TEXT NOT NULL,
                    sql_text TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    elapsed_ms REAL,
                    created_at TEXT NOT NULL
                )
                """
            ))

    def seed_demo_data(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text(
                """
                CREATE TABLE IF NOT EXISTS products (
                    product TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    unit_price REAL NOT NULL
                )
                """
            ))
            connection.execute(text(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY,
                    order_date TEXT NOT NULL,
                    region TEXT NOT NULL,
                    product TEXT NOT NULL REFERENCES products(product),
                    quantity INTEGER NOT NULL,
                    amount REAL NOT NULL
                )
                """
            ))
            if connection.execute(text("SELECT COUNT(*) FROM sales")).scalar_one():
                return
            connection.execute(
                text("INSERT INTO products (product, category, unit_price) VALUES (:p, :c, :u)"),
                [
                    {"p": "Agent 工作台", "c": "平台", "u": 1400.0},
                    {"p": "知识库服务", "c": "服务", "u": 1500.0},
                    {"p": "数据分析助手", "c": "平台", "u": 1800.0},
                ],
            )
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
                    "INSERT INTO sales (order_date, region, product, quantity, amount) "
                    "VALUES (:order_date, :region, :product, :quantity, :amount)"
                ),
                [dict(zip(("order_date", "region", "product", "quantity", "amount"), row)) for row in rows],
            )

    def tables(self) -> dict[str, list[str]]:
        inspector = inspect(self.engine)
        return {
            name: [f"{column['name']} {column['type']}" for column in inspector.get_columns(name)]
            for name in inspector.get_table_names()
            if name != "query_history"
        }

    def schema_text(self, question: str | None = None) -> str:
        """Schema of the tables relevant to the question (all tables when nothing matches)."""
        tables = self.tables()
        selected = [name for name in tables if question and _table_matches(name, tables[name], question)]
        chosen = selected or list(tables)
        return "\n".join(f"{name}({', '.join(tables[name])})" for name in chosen)

    def execute_readonly(
        self, sql: str, max_rows: int = 200, timeout_seconds: float = 3.0
    ) -> tuple[list[str], list[dict[str, Any]], bool]:
        """Run one validated SELECT; returns (columns, rows, truncated)."""
        with self.readonly_engine.connect() as connection:
            raw = connection.connection.dbapi_connection
            if self.is_sqlite:
                deadline = time.monotonic() + timeout_seconds
                # SQLite calls this every N VM steps; a non-zero return aborts the running query.
                raw.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            try:
                result = connection.execute(text(sql))
                columns = list(result.keys())
                fetched = result.fetchmany(max_rows + 1)
            except Exception as exc:
                if self.is_sqlite and "interrupted" in str(exc):
                    raise QueryTimeout(f"查询超过 {timeout_seconds} 秒被中止") from exc
                raise
            finally:
                if self.is_sqlite:
                    raw.set_progress_handler(None, 0)
                connection.rollback()
        rows = [dict(row._mapping) for row in fetched[:max_rows]]
        return columns, rows, len(fetched) > max_rows

    def record_history(
        self, question: str, sql: str, row_count: int, status: str,
        reason: str | None = None, elapsed_ms: float | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO query_history (question, sql_text, row_count, status, reason, elapsed_ms, created_at) "
                    "VALUES (:question, :sql_text, :row_count, :status, :reason, :elapsed_ms, :created_at)"
                ),
                {
                    "question": question,
                    "sql_text": sql,
                    "row_count": row_count,
                    "status": status,
                    "reason": reason,
                    "elapsed_ms": elapsed_ms,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT id, question, sql_text, row_count, status, reason, elapsed_ms, created_at "
                    "FROM query_history ORDER BY id DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
            return [dict(row._mapping) for row in result.fetchall()]


def _sqlite_query_only(dbapi_connection, _record) -> None:
    dbapi_connection.execute("PRAGMA query_only = ON")


def _table_matches(table: str, columns: list[str], question: str) -> bool:
    lowered = question.lower()
    names = [table] + [column.split()[0] for column in columns]
    aliases = " ".join(SCHEMA_ALIASES.get(key, "") for key in [table] + [f"{table}.{n}" for n in names[1:]])
    words = names + aliases.split()
    return any(re.search(re.escape(word.lower()), lowered) for word in words if word)
