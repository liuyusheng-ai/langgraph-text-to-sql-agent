"""Six-node LangGraph workflow for safe Text-to-SQL analysis."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .charting import build_chart_spec
from .database import AgentDatabase, QueryTimeout
from .llm import DemoSQLGenerator
from .safety import SQLSafetyValidator

# Requests to change or remove data are refused before any SQL is generated.
WRITE_INTENT = re.compile(
    r"删除|删掉|清空|清除|修改|更新|改成|插入|新增一条|添加一条|写入|新建|创建|建表|删表|备份表|授权|"
    r"\b(drop|delete|update|insert|truncate|alter|create|grant)\b",
    flags=re.I,
)


class QueryState(TypedDict, total=False):
    question: str
    intent: str
    schema: str
    sql: str
    safe_sql: str
    validation_error: str | None
    rejection: str | None
    repair_count: int
    columns: list[str]
    rows: list[dict[str, Any]]
    truncated: bool
    explanation: str
    chart: dict[str, Any] | None
    status: str
    elapsed_ms: float


class TextToSQLAgent:
    def __init__(
        self,
        database: AgentDatabase,
        generator: DemoSQLGenerator | None = None,
        max_rows: int = 200,
        max_repairs: int = 1,
        timeout_seconds: float = 3.0,
        max_question_chars: int = 500,
    ) -> None:
        self.database = database
        self.generator = generator or DemoSQLGenerator()
        self.validator = SQLSafetyValidator(max_rows=max_rows)
        self.max_rows = max_rows
        self.max_repairs = max_repairs
        self.timeout_seconds = timeout_seconds
        self.max_question_chars = max_question_chars
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(QueryState)
        graph.add_node("understand_question", self._understand_question)
        graph.add_node("retrieve_schema", self._retrieve_schema)
        graph.add_node("generate_sql", self._generate_sql)
        graph.add_node("validate_sql", self._validate_sql)
        graph.add_node("execute_sql", self._execute_sql)
        graph.add_node("explain_result", self._explain_result)

        graph.add_edge(START, "understand_question")
        graph.add_conditional_edges(
            "understand_question",
            lambda state: "reject" if state.get("rejection") else "continue",
            {"continue": "retrieve_schema", "reject": "explain_result"},
        )
        graph.add_edge("retrieve_schema", "generate_sql")
        graph.add_edge("generate_sql", "validate_sql")
        graph.add_conditional_edges(
            "validate_sql",
            self._route_after_validation,
            {"execute": "execute_sql", "repair": "generate_sql", "reject": "explain_result"},
        )
        graph.add_edge("execute_sql", "explain_result")
        graph.add_edge("explain_result", END)
        return graph.compile()

    def run(self, question: str) -> QueryState:
        started = time.perf_counter()
        result = self.graph.invoke({"question": (question or "").strip(), "repair_count": 0, "status": "started"})
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        self.database.record_history(
            result["question"] or "(空)",
            result.get("safe_sql") or result.get("sql") or "",
            len(result.get("rows") or []),
            result["status"],
            reason=result.get("rejection") or result.get("validation_error"),
            elapsed_ms=result["elapsed_ms"],
        )
        return result

    def _understand_question(self, state: QueryState) -> QueryState:
        question = state["question"]
        if not question:
            return {"intent": "invalid", "rejection": "问题为空"}
        if len(question) > self.max_question_chars:
            return {"intent": "invalid", "rejection": f"问题超过 {self.max_question_chars} 个字符"}
        if WRITE_INTENT.search(question):
            return {"intent": "write", "rejection": "只支持查询分析，不支持修改或删除数据"}
        return {"intent": "analysis", "rejection": None, "status": "understood"}

    def _retrieve_schema(self, state: QueryState) -> QueryState:
        return {"schema": self.database.schema_text(state["question"]), "status": "schema_loaded"}

    def _generate_sql(self, state: QueryState) -> QueryState:
        repair_count = state.get("repair_count", 0) + (1 if state.get("validation_error") else 0)
        sql = self.generator.generate(state["question"], state.get("schema", ""), state.get("validation_error"))
        return {"sql": sql, "repair_count": repair_count, "validation_error": None, "status": "sql_generated"}

    def _validate_sql(self, state: QueryState) -> QueryState:
        result = self.validator.validate(state.get("sql", ""))
        if result.is_safe:
            return {"safe_sql": result.sql, "validation_error": None, "status": "validated"}
        return {"safe_sql": "", "validation_error": result.reason, "status": "blocked"}

    def _route_after_validation(self, state: QueryState) -> str:
        if not state.get("validation_error"):
            return "execute"
        if state.get("repair_count", 0) < self.max_repairs:
            return "repair"
        return "reject"

    def _execute_sql(self, state: QueryState) -> QueryState:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.database.execute_readonly, state["safe_sql"], self.max_rows, self.timeout_seconds
        )
        try:
            # The database enforces the timeout itself where it can (SQLite); this is the outer bound.
            columns, rows, truncated = future.result(timeout=self.timeout_seconds + 1)
            return {"columns": columns, "rows": rows, "truncated": truncated, "status": "executed"}
        except (QueryTimeout, FutureTimeout):
            return {"columns": [], "rows": [], "validation_error": "查询执行超时", "status": "timeout"}
        except Exception as exc:
            return {"columns": [], "rows": [], "validation_error": f"查询执行失败：{exc}", "status": "failed"}
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _explain_result(self, state: QueryState) -> QueryState:
        reason = state.get("rejection") or state.get("validation_error")
        if reason:
            status = state.get("status") if state.get("status") in {"timeout", "failed"} else "rejected"
            return {"explanation": f"请求未执行：{reason}", "chart": None, "status": status}
        columns, rows = state.get("columns", []), state.get("rows", [])
        explanation = self.generator.explain(state["question"], columns, rows)
        if state.get("truncated"):
            explanation += f"（结果超过 {self.max_rows} 行，仅返回前 {self.max_rows} 行）"
        return {"explanation": explanation, "chart": build_chart_spec(columns, rows), "status": "completed"}
