"""FastAPI entrypoint for the Text-to-SQL Agent."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from sql_agent import AgentDatabase, TextToSQLAgent


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class QueryResponse(BaseModel):
    question: str
    sql: str | None
    status: str
    explanation: str
    columns: list[str]
    rows: list[dict[str, Any]]
    chart: dict[str, Any] | None
    truncated: bool = False
    elapsed_ms: float | None = None


database = AgentDatabase(os.getenv("DATABASE_URL", "sqlite:///data/analytics.db"))
database.seed_demo_data()
agent = TextToSQLAgent(database)

app = FastAPI(
    title="LangGraph Text-to-SQL Agent",
    version="1.0.0",
    description="Natural-language analytics with bounded read-only SQL execution.",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = agent.run(request.question)
    return QueryResponse(
        question=request.question,
        sql=result.get("safe_sql") or result.get("sql"),
        status=result.get("status", "unknown"),
        explanation=result.get("explanation", ""),
        columns=result.get("columns", []),
        rows=result.get("rows", []),
        chart=result.get("chart"),
        truncated=bool(result.get("truncated")),
        elapsed_ms=result.get("elapsed_ms"),
    )


@app.get("/api/history")
def history(limit: int = 20) -> dict[str, Any]:
    bounded_limit = min(max(limit, 1), 100)
    return {"items": database.history(bounded_limit)}

