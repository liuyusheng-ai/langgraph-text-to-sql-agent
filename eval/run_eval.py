"""Offline, reproducible evaluation of answers, refusals and the SQL safety boundary.

    python eval/run_eval.py            # writes eval/results.json and eval/RESULTS.md

Normal questions run end to end through the LangGraph workflow with the rule-based demo
generator; a case passes when its rows equal the reference SQL's rows. Latency therefore
covers routing, validation and execution, not SQL generation by a language model.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sql_agent import AgentDatabase, TextToSQLAgent  # noqa: E402
from sql_agent.safety import SQLSafetyValidator  # noqa: E402


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return round(ordered[index], 2)


def as_bag(rows) -> Counter:
    return Counter(tuple(round(v, 2) if isinstance(v, float) else v for v in row) for row in rows)


def main() -> int:
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        database = AgentDatabase(f"sqlite:///{Path(tmp) / 'eval.db'}")
        database.seed_demo_data()
        agent = TextToSQLAgent(database)
        agent.run("预热")  # first graph run compiles lazily; keep it out of the latency figures
        validator = SQLSafetyValidator()

        normal = []
        for case in cases["normal_queries"]:
            result = agent.run(case["question"])
            expected = database.execute_readonly(case["reference_sql"], max_rows=10_000)[1]
            got = [tuple(row.values()) for row in result.get("rows", [])]
            passed = result["status"] == "completed" and as_bag(got) == as_bag(tuple(r.values()) for r in expected)
            normal.append({"id": case["id"], "question": case["question"], "status": result["status"],
                           "rows": len(got), "elapsed_ms": result["elapsed_ms"], "passed": passed})

        dangerous = []
        for case in cases["dangerous_requests"]:
            result = agent.run(case["question"])
            dangerous.append({"id": case["id"], "question": case["question"], "status": result["status"],
                              "reason": result["explanation"], "elapsed_ms": result["elapsed_ms"],
                              "passed": result["status"] == "rejected" and not result.get("rows")})

        adversarial = []
        for case in cases["adversarial_sql"]:
            started = time.perf_counter()
            verdict = validator.validate(case["sql"])
            adversarial.append({"id": case["id"], "sql": case["sql"], "blocked": not verdict.is_safe,
                                "reason": verdict.reason, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                                "passed": not verdict.is_safe})

        benign = []
        for case in cases["benign_sql"]:
            verdict = validator.validate(case["sql"])
            executed = False
            if verdict.is_safe:
                database.execute_readonly(verdict.sql)
                executed = True
            benign.append({"id": case["id"], "sql": case["sql"], "allowed": verdict.is_safe,
                           "reason": verdict.reason, "passed": executed})

    latencies = [row["elapsed_ms"] for row in normal + dangerous]
    summary = {
        "normal_passed": sum(r["passed"] for r in normal), "normal_total": len(normal),
        "dangerous_refused": sum(r["passed"] for r in dangerous), "dangerous_total": len(dangerous),
        "adversarial_blocked": sum(r["passed"] for r in adversarial), "adversarial_total": len(adversarial),
        "benign_allowed": sum(r["passed"] for r in benign), "benign_total": len(benign),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
    }
    summary["cases_passed"] = sum(summary[k] for k in ("normal_passed", "dangerous_refused", "adversarial_blocked", "benign_allowed"))
    summary["cases_total"] = sum(summary[k] for k in ("normal_total", "dangerous_total", "adversarial_total", "benign_total"))
    out = {"summary": summary, "normal": normal, "dangerous": dangerous, "adversarial": adversarial, "benign": benign}
    (ROOT / "eval" / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "eval" / "RESULTS.md").write_text(render_markdown(out), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["cases_passed"] == summary["cases_total"] else 1


def mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(out: dict) -> str:
    s = out["summary"]
    lines = [
        "# 评测结果",
        "",
        "由 `python eval/run_eval.py` 生成。正常问题端到端运行 LangGraph 工作流（规则版 SQL 生成器），"
        "结果与参考 SQL 的结果逐行比对；不调用大模型。",
        "",
        "| 类别 | 结果 |",
        "| --- | --- |",
        f"| 正常查询结果正确 | {s['normal_passed']}/{s['normal_total']} |",
        f"| 危险自然语言请求被拒绝 | {s['dangerous_refused']}/{s['dangerous_total']} |",
        f"| 对抗 SQL 被拦截 | {s['adversarial_blocked']}/{s['adversarial_total']} |",
        f"| 正常但易误判的 SQL 放行并执行 | {s['benign_allowed']}/{s['benign_total']} |",
        f"| 合计 | {s['cases_passed']}/{s['cases_total']} |",
        f"| 端到端延迟 P50 / P95 | {s['latency_p50_ms']} ms / {s['latency_p95_ms']} ms |",
        "",
        "## 正常查询", "", "| ID | 问题 | 状态 | 行数 | 耗时 ms | 通过 |", "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {r['id']} | {r['question']} | {r['status']} | {r['rows']} | {r['elapsed_ms']} | {mark(r['passed'])} |" for r in out["normal"]]
    lines += ["", "## 危险请求", "", "| ID | 问题 | 结果 | 通过 |", "| --- | --- | --- | --- |"]
    lines += [f"| {r['id']} | {cell(r['question']) or '(空白)'} | {cell(r['reason'])} | {mark(r['passed'])} |" for r in out["dangerous"]]
    lines += ["", "## 对抗 SQL", "", "| ID | SQL | 拦截原因 | 通过 |", "| --- | --- | --- | --- |"]
    lines += [f"| {r['id']} | `{cell(r['sql'])}` | {cell(r['reason'])} | {mark(r['passed'])} |" for r in out["adversarial"]]
    lines += ["", "## 易误判的正常 SQL", "", "| ID | SQL | 通过 |", "| --- | --- | --- |"]
    lines += [f"| {r['id']} | `{cell(r['sql'])}` | {mark(r['passed'])} |" for r in out["benign"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
