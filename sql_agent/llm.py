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


class OllamaSQLGenerator(DemoSQLGenerator):
    """SQL generation with a local model served by Ollama (http://localhost:11434).

    Uses only the standard library. Every call's token counts and latency are kept in
    `self.calls` so evaluations can report cost alongside accuracy.
    """

    SYSTEM_PROMPT = (
        "You are an expert data analyst who writes SQLite queries.\n"
        "Rules:\n"
        "- Answer with exactly one SQLite SELECT (or WITH ... SELECT) statement inside a ```sql code block.\n"
        "- Use only tables and columns that appear in the schema; copy quoted names exactly, quotes included.\n"
        "- Select only the columns the question asks for, in the order it asks for them.\n"
        "- Never modify data."
    )

    def __init__(
        self,
        model: str = "qwen3.5:4b",
        host: str = "http://localhost:11434",
        temperature: float = 0.0,
        num_ctx: int = 16384,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout_seconds = timeout_seconds
        self.calls: list[dict] = []

    def generate(self, question: str, schema: str, error: str | None = None) -> str:
        prompt = f"Database schema:\n{schema}\n\nQuestion: {question}"
        if error:
            prompt += (
                f"\n\nYour previous query did not work.\n{error}\n"
                "Fix the problem and answer with the corrected query."
            )
        content = self._chat(prompt)
        return extract_sql(content)

    def _chat(self, prompt: str) -> str:
        import json
        import time
        import urllib.request

        body = json.dumps({
            "model": self.model,
            "stream": False,
            "think": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host}/api/chat", data=body, headers={"Content-Type": "application/json"}
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read())
        self.calls.append({
            "prompt_tokens": payload.get("prompt_eval_count", 0),
            "completion_tokens": payload.get("eval_count", 0),
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        })
        return payload["message"]["content"]


def extract_sql(text: str) -> str:
    """Take the SQL out of a fenced code block, or the first SELECT/WITH statement in plain text."""
    fenced = re.findall(r"```(?:sql|sqlite)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        return fenced[-1].strip()
    match = re.search(r"\b(SELECT|WITH)\b.*", text, flags=re.S | re.I)
    return (match.group(0) if match else text).strip()
