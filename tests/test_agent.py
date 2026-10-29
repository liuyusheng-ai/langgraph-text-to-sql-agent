from pathlib import Path

import pytest

from sql_agent import AgentDatabase, TextToSQLAgent
from sql_agent.llm import DemoSQLGenerator


class ScriptedGenerator(DemoSQLGenerator):
    def __init__(self, sqls: list[str]) -> None:
        self.sqls = list(sqls)
        self.errors: list[str | None] = []

    def generate(self, question, schema, error=None):
        self.errors.append(error)
        return self.sqls.pop(0) if len(self.sqls) > 1 else self.sqls[0]


@pytest.fixture()
def database(tmp_path: Path) -> AgentDatabase:
    db = AgentDatabase(f"sqlite:///{tmp_path / 'test.db'}")
    db.seed_demo_data()
    return db


def make_agent(database: AgentDatabase, **kwargs) -> TextToSQLAgent:
    return TextToSQLAgent(database, **kwargs)


def test_region_analysis_returns_rows_and_chart(database) -> None:
    result = make_agent(database).run("统计各地区销售额")
    assert result["status"] == "completed"
    assert result["columns"] == ["region", "total_amount"]
    assert len(result["rows"]) == 3
    assert result["chart"]["data"][0]["type"] == "bar"


def test_write_request_is_rejected_before_sql_generation(database) -> None:
    generator = ScriptedGenerator(["SELECT 1"])
    result = make_agent(database, generator=generator).run("删除全部销售数据")
    assert result["status"] == "rejected"
    assert generator.errors == []
    assert "不支持修改或删除" in result["explanation"]


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_blank_question_is_rejected_not_executed(database, question) -> None:
    result = make_agent(database).run(question)
    assert result["status"] == "rejected"
    assert not result.get("rows")
    assert "问题为空" in result["explanation"]


def test_generated_dangerous_sql_is_blocked_after_bounded_repair(database) -> None:
    generator = ScriptedGenerator(["DROP TABLE sales"])
    result = make_agent(database, generator=generator, max_repairs=2).run("统计销售额")
    assert result["status"] == "rejected"
    assert result["repair_count"] == 2
    assert generator.errors == [None, "仅允许 SELECT 或 WITH 查询", "仅允许 SELECT 或 WITH 查询"]


def test_repair_path_recovers_with_valid_sql(database) -> None:
    generator = ScriptedGenerator(["SELECT * FROM sales; DROP TABLE sales", "SELECT COUNT(*) AS n FROM sales"])
    result = make_agent(database, generator=generator).run("统计订单数")
    assert result["status"] == "completed"
    assert result["repair_count"] == 1
    assert result["rows"] == [{"n": 8}]


def test_row_limit_applies_even_when_a_cte_has_its_own_limit(database) -> None:
    sql = (
        "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 1000) "
        "SELECT x FROM n WHERE x IN (SELECT id FROM sales LIMIT 3) OR x > 0"
    )
    result = make_agent(database, generator=ScriptedGenerator([sql]), max_rows=50).run("统计")
    assert result["status"] == "completed"
    assert len(result["rows"]) == 50
    assert result["truncated"] is False  # the wrapped LIMIT cut it to exactly max_rows


def test_truncation_is_reported_when_database_returns_more_rows(database) -> None:
    agent = make_agent(database, max_rows=3)
    columns, rows, truncated = database.execute_readonly("SELECT * FROM sales", max_rows=3)
    assert (len(rows), truncated) == (3, True)
    assert agent.run("列出订单明细")["rows"].__len__() == 3


def test_readonly_connection_refuses_writes_even_without_validator(database) -> None:
    with pytest.raises(Exception, match="readonly|read-only|query_only|attempt to write"):
        database.execute_readonly("DELETE FROM sales")
    assert database.execute_readonly("SELECT COUNT(*) AS n FROM sales")[1] == [{"n": 8}]


def test_runaway_query_is_interrupted_by_timeout(database) -> None:
    sql = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) SELECT COUNT(*) AS c FROM n"
    agent = make_agent(database, generator=ScriptedGenerator([sql]), timeout_seconds=0.2)
    result = agent.run("统计")
    assert result["status"] == "timeout"
    assert result["elapsed_ms"] < 2000


def test_schema_retrieval_selects_relevant_tables(database) -> None:
    assert database.schema_text("各产品单价是多少").startswith("products(")
    assert "products(" not in database.schema_text("各地区订单数")
    assert set(line.split("(")[0] for line in database.schema_text("火星天气").splitlines()) == {"products", "sales"}


def test_join_query_by_category(database) -> None:
    result = make_agent(database).run("按产品类别统计销售额")
    assert result["status"] == "completed"
    assert {row["category"] for row in result["rows"]} == {"平台", "服务"}


def test_query_history_records_success_and_rejection(database) -> None:
    agent = make_agent(database)
    agent.run("统计产品销售额")
    agent.run("删除全部销售数据")
    history = agent.database.history()
    assert [item["status"] for item in history] == ["rejected", "completed"]
    assert history[0]["reason"] == "只支持查询分析，不支持修改或删除数据"
