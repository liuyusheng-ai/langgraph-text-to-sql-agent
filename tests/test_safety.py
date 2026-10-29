import pytest

from sql_agent.safety import SQLSafetyValidator

validator = SQLSafetyValidator(max_rows=50)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE sales",
        "SELECT * FROM sales; DROP TABLE sales",
        "SELECT * FROM sales;DELETE FROM sales",
        "WITH t AS (SELECT 1) DELETE FROM sales",
        "SELECT * INTO backup FROM sales",
        "SELECT load_extension('/tmp/evil.so')",
        "SELECT randomblob(1000000000)",
        "SELECT pg_sleep(30)",
        "SELECT readfile('/etc/passwd')",
        "PRAGMA table_info(sales)",
        "ATTACH DATABASE '/tmp/x.db' AS x",
        "/* hi */ UPDATE sales SET amount = 0",
        "SELECT 1 -- ok\n; DROP TABLE sales",
        "REPLACE INTO sales VALUES (1)",
    ],
)
def test_dangerous_sql_is_blocked(sql: str) -> None:
    assert not validator.validate(sql).is_safe


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT REPLACE(product, ' ', '') AS name FROM sales",
        "SELECT * FROM sales WHERE product = 'update; drop'",
        "SELECT * FROM sales WHERE product LIKE '%delete%'",
        "SELECT \"order_date\" FROM sales",
        "WITH t AS (SELECT region, amount FROM sales) SELECT region, SUM(amount) FROM t GROUP BY region",
        "select offset_value from (select 1 as offset_value)",
    ],
)
def test_benign_sql_is_not_a_false_positive(sql: str) -> None:
    assert validator.validate(sql).is_safe, validator.validate(sql).reason


def test_row_limit_wraps_the_outer_query() -> None:
    bounded = validator.validate("WITH t AS (SELECT * FROM sales LIMIT 5) SELECT * FROM sales LIMIT 999").sql
    assert bounded.startswith("SELECT * FROM (WITH t AS")
    assert bounded.endswith("LIMIT 50")


def test_overlong_sql_is_rejected() -> None:
    result = SQLSafetyValidator(max_sql_chars=20).validate("SELECT * FROM sales WHERE 1 = 1")
    assert not result.is_safe and "字符" in result.reason


def test_empty_sql_is_rejected() -> None:
    assert validator.validate("  ;  ").reason == "SQL 为空"
