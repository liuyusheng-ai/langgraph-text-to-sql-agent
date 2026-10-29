"""Replaceable model adapter with an offline, rule-based demo implementation.

A real model only has to implement `generate(question, schema, error)` and `explain(...)`;
whatever it returns still goes through SQLSafetyValidator before execution.
"""

from __future__ import annotations

import re

REGIONS = ("华北", "华东", "华南")


class DemoSQLGenerator:
    """Deterministic SQL for the demo dataset, so the project runs and tests without an API key."""

    def generate(self, question: str, schema: str, error: str | None = None) -> str:
        region = next((name for name in REGIONS if name in question), None)
        where = f" WHERE region = '{region}'" if region else ""

        if re.search(r"类别|品类|分类", question):
            return (
                "SELECT p.category, SUM(s.quantity) AS total_quantity, ROUND(SUM(s.amount), 2) AS total_amount "
                "FROM sales s JOIN products p ON p.product = s.product "
                "GROUP BY p.category ORDER BY total_amount DESC"
            )
        if re.search(r"单价|价格", question):
            return "SELECT product, category, unit_price FROM products ORDER BY unit_price DESC"
        if re.search(r"平均", question):
            return f"SELECT ROUND(AVG(amount), 2) AS avg_amount FROM sales{where}"
        if re.search(r"最高|最多|第一|top", question, flags=re.I) and "产品" in question:
            return (
                f"SELECT product, ROUND(SUM(amount), 2) AS total_amount FROM sales{where} "
                "GROUP BY product ORDER BY total_amount DESC LIMIT 1"
            )
        by_region = re.search(r"各(地区|区域)|按(地区|区域)|每个(地区|区域)|(地区|区域)(对比|排名)", question)
        if by_region and re.search(r"订单数|单数|几笔|多少笔", question):
            return "SELECT region, COUNT(*) AS order_count FROM sales GROUP BY region ORDER BY order_count DESC"
        if by_region:
            return (
                "SELECT region, ROUND(SUM(amount), 2) AS total_amount "
                "FROM sales GROUP BY region ORDER BY total_amount DESC"
            )
        if "产品" in question:
            return (
                f"SELECT product, SUM(quantity) AS total_quantity, ROUND(SUM(amount), 2) AS total_amount "
                f"FROM sales{where} GROUP BY product ORDER BY total_amount DESC"
            )
        if re.search(r"月份|月度|趋势|每月", question):
            return (
                f"SELECT SUBSTR(order_date, 1, 7) AS month, ROUND(SUM(amount), 2) AS total_amount "
                f"FROM sales{where} GROUP BY SUBSTR(order_date, 1, 7) ORDER BY month"
            )
        if re.search(r"多少|一共|总共|合计|总额", question) and not re.search(r"明细|列出", question):
            return f"SELECT COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_amount FROM sales{where}"
        if re.search(r"明细|列出|订单", question):
            return f"SELECT order_date, region, product, quantity, amount FROM sales{where} ORDER BY order_date DESC"
        return f"SELECT COUNT(*) AS order_count, ROUND(SUM(amount), 2) AS total_amount FROM sales{where}"

    def explain(self, question: str, columns: list[str], rows: list[dict]) -> str:
        if not rows:
            return "查询执行成功，但没有返回符合条件的数据。"
        if len(rows) == 1:
            values = "，".join(f"{key}={value}" for key, value in rows[0].items())
            return f"根据当前数据，{values}。"
        return f"查询返回 {len(rows)} 行结果，可结合图表比较主要差异。"
