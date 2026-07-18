"""Six-node LangGraph workflow for safe Text-to-SQL analysis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from charting import build_chart_spec
from database import AgentDatabase
from llm import DemoSQLGenerator
from safety import SQLSafetyValidator


class QueryState(TypedDict, total=False):
    question: str
    intent: str
    schema: str
    sql: str
    safe_sql: str
    validation_error: str | None
    repair_count: int
    columns: list[str]
    rows: list[dict[str, Any]]
    explanation: str
    chart: dict[str, Any] | None
    status: str


class TextToSQLAgent:
    def __init__(
        self,
        database: AgentDatabase,
        generator: DemoSQLGenerator | None = None,
        max_rows: int = 200,
        max_repairs: int = 1,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.database = database
        self.generator = generator or DemoSQLGenerator()
        self.validator = SQLSafetyValidator(max_rows=max_rows)
        self.max_repairs = max_repairs
        self.timeout_seconds = timeout_seconds
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
        graph.add_edge("understand_question", "retrieve_schema")
        graph.add_edge("retrieve_schema", "generate_sql")
        graph.add_edge("generate_sql", "validate_sql")
        graph.add_conditional_edges(
            "validate_sql",
            self._route_after_validation,
            {
                "execute": "execute_sql",
                "repair": "generate_sql",
                "reject": "explain_result",
            },
        )
        graph.add_edge("execute_sql", "explain_result")
        graph.add_edge("explain_result", END)
        return graph.compile()

    def run(self, question: str) -> QueryState:
        initial: QueryState = {
            "question": question.strip(),
            "repair_count": 0,
            "status": "started",
        }
        return self.graph.invoke(initial)

    def _understand_question(self, state: QueryState) -> QueryState:
        question = state["question"]
        if not question:
            return {"intent": "invalid", "status": "rejected"}
        return {"intent": "aggregate_analysis", "status": "understood"}

    def _retrieve_schema(self, state: QueryState) -> QueryState:
        return {"schema": self.database.schema_text(), "status": "schema_loaded"}

    def _generate_sql(self, state: QueryState) -> QueryState:
        repair_count = state.get("repair_count", 0)
        if state.get("validation_error"):
            repair_count += 1
        sql = self.generator.generate(
            state["question"],
            state.get("schema", ""),
            state.get("validation_error"),
        )
        return {
            "sql": sql,
            "repair_count": repair_count,
            "validation_error": None,
            "status": "sql_generated",
        }

    def _validate_sql(self, state: QueryState) -> QueryState:
        result = self.validator.validate(state.get("sql", ""))
        if result.is_safe:
            return {
                "safe_sql": result.sql,
                "validation_error": None,
                "status": "validated",
            }
        return {
            "safe_sql": "",
            "validation_error": result.reason,
            "status": "blocked",
        }

    def _route_after_validation(self, state: QueryState) -> str:
        if not state.get("validation_error"):
            return "execute"
        if state.get("repair_count", 0) < self.max_repairs:
            return "repair"
        return "reject"

    def _execute_sql(self, state: QueryState) -> QueryState:
        sql = state["safe_sql"]
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.database.execute_readonly, sql)
        try:
            columns, rows = future.result(timeout=self.timeout_seconds)
            self.database.record_history(
                state["question"], sql, len(rows), "success"
            )
            return {
                "columns": columns,
                "rows": rows,
                "status": "executed",
            }
        except FutureTimeout:
            future.cancel()
            self.database.record_history(state["question"], sql, 0, "timeout")
            return {
                "columns": [],
                "rows": [],
                "validation_error": "查询执行超时",
                "status": "timeout",
            }
        except Exception as exc:
            self.database.record_history(state["question"], sql, 0, "failed")
            return {
                "columns": [],
                "rows": [],
                "validation_error": f"查询执行失败：{exc}",
                "status": "failed",
            }
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _explain_result(self, state: QueryState) -> QueryState:
        if state.get("validation_error"):
            return {
                "explanation": f"请求未执行：{state['validation_error']}",
                "chart": None,
                "status": "rejected",
            }
        columns = state.get("columns", [])
        rows = state.get("rows", [])
        return {
            "explanation": self.generator.explain(
                state["question"], columns, rows
            ),
            "chart": build_chart_spec(columns, rows),
            "status": "completed",
        }

