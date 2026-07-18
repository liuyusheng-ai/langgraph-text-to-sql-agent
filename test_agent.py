from pathlib import Path

from database import AgentDatabase
from safety import SQLSafetyValidator
from workflow import TextToSQLAgent


def make_agent(tmp_path: Path) -> TextToSQLAgent:
    database = AgentDatabase(f"sqlite:///{tmp_path / 'test.db'}")
    database.seed_demo_data()
    return TextToSQLAgent(database)


def test_region_analysis_returns_rows_and_chart(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    result = agent.run("统计各地区销售额")
    assert result["status"] == "completed"
    assert result["columns"] == ["region", "total_amount"]
    assert len(result["rows"]) == 3
    assert result["chart"]["data"][0]["type"] == "bar"


def test_write_operation_is_rejected(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    result = agent.run("删除全部销售数据")
    assert result["status"] == "rejected"
    assert "禁止" in result["explanation"] or "仅允许" in result["explanation"]


def test_row_limit_is_added_and_bounded() -> None:
    validator = SQLSafetyValidator(max_rows=50)
    assert validator.validate("SELECT * FROM sales").sql.endswith("LIMIT 50")
    assert validator.validate("SELECT * FROM sales LIMIT 999").sql.endswith(
        "LIMIT 50"
    )


def test_multiple_statements_are_rejected() -> None:
    validator = SQLSafetyValidator()
    result = validator.validate("SELECT * FROM sales; DROP TABLE sales")
    assert not result.is_safe


def test_query_history_is_recorded(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    agent.run("统计产品销售额")
    history = agent.database.history()
    assert len(history) == 1
    assert history[0]["status"] == "success"

