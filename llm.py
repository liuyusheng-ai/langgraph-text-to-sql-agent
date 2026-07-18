"""Replaceable model adapter with an offline demo implementation."""

from __future__ import annotations


class DemoSQLGenerator:
    """Generate deterministic SQL so the project works without an API key."""

    def generate(self, question: str, schema: str, error: str | None = None) -> str:
        normalized = question.lower()
        if any(word in normalized for word in ("删除", "drop", "清空", "update")):
            return "DROP TABLE sales"
        if "地区" in question or "区域" in question:
            return (
                "SELECT region, ROUND(SUM(amount), 2) AS total_amount "
                "FROM sales GROUP BY region ORDER BY total_amount DESC"
            )
        if "产品" in question:
            return (
                "SELECT product, SUM(quantity) AS total_quantity, "
                "ROUND(SUM(amount), 2) AS total_amount "
                "FROM sales GROUP BY product ORDER BY total_amount DESC"
            )
        if "月份" in question or "月度" in question or "趋势" in question:
            return (
                "SELECT SUBSTR(order_date, 1, 7) AS month, "
                "ROUND(SUM(amount), 2) AS total_amount "
                "FROM sales GROUP BY SUBSTR(order_date, 1, 7) ORDER BY month"
            )
        if "订单" in question or "明细" in question:
            return (
                "SELECT order_date, region, product, quantity, amount "
                "FROM sales ORDER BY order_date DESC"
            )
        return (
            "SELECT COUNT(*) AS order_count, "
            "ROUND(SUM(amount), 2) AS total_amount FROM sales"
        )

    def explain(
        self, question: str, columns: list[str], rows: list[dict]
    ) -> str:
        if not rows:
            return "查询执行成功，但没有返回符合条件的数据。"
        if len(rows) == 1:
            values = "，".join(f"{key}={value}" for key, value in rows[0].items())
            return f"根据当前数据，{values}。"
        return f"查询返回 {len(rows)} 行结果，可结合图表比较主要差异。"

