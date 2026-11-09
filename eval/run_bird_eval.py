"""Evaluate the agent with a real model on a stratified sample of BIRD Mini-Dev (SQLite).

    # 1. Download https://bird-bench.oss-cn-beijing.aliyuncs.com/minidev.zip and unzip it
    # 2. Start Ollama and pull the model, e.g. `ollama pull qwen3.5:4b`
    python eval/run_bird_eval.py --data-dir path/to/minidev/MINIDEV

Metrics
- Execution accuracy (EX), BIRD's official definition: the predicted query's result set equals
  the gold query's result set (row order ignored), reported per difficulty.
- Self-repair ablation: the same run also scores the first generated SQL on its own. With
  temperature 0 that is exactly what the agent returns when `max_repairs=0`, so the difference
  is what the repair loop (validation errors and execution errors fed back to the model) adds.
- Safety false positives on all 500 Mini-Dev items: gold SQL blocked by the validator, and
  questions refused by the write-intent check. Neither needs a model.
- Latency and tokens per question.

Writes eval/bird/results.json and eval/bird/RESULTS.md.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sql_agent import AgentDatabase, TextToSQLAgent  # noqa: E402
from sql_agent.llm import OllamaSQLGenerator  # noqa: E402
from sql_agent.safety import SQLSafetyValidator  # noqa: E402
from sql_agent.workflow import WRITE_INTENT  # noqa: E402

LEVELS = ("simple", "moderate", "challenging")
MAX_ROWS = 100_000


class EvalDatabase(AgentDatabase):
    """BIRD databases are not ours to write to: keep query history in memory instead."""

    def __init__(self, database_url: str) -> None:
        self.memory_history: list[dict[str, Any]] = []
        super().__init__(database_url)

    def _create_history_table(self) -> None:
        pass

    def record_history(self, question, sql, row_count, status, reason=None, elapsed_ms=None) -> None:
        self.memory_history.append({"question": question, "status": status})


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)
    connection.text_factory = lambda b: b.decode(errors="replace")
    return connection


def run_sql(connection: sqlite3.Connection, sql: str, timeout_seconds: float) -> set[tuple]:
    deadline = time.monotonic() + timeout_seconds
    connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
    try:
        return set(connection.execute(sql).fetchmany(MAX_ROWS))
    finally:
        connection.set_progress_handler(None, 0)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return round(ordered[index], 1)


def question_text(item: dict) -> str:
    evidence = (item.get("evidence") or "").strip()
    return f"{item['question']}\nHint: {evidence}" if evidence else item["question"]


def sample(items: list[dict], per_level: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    chosen = []
    for level in LEVELS:
        pool = sorted((x for x in items if x["difficulty"] == level), key=lambda x: x["question_id"])
        chosen += rng.sample(pool, min(per_level, len(pool)))
    return sorted(chosen, key=lambda x: x["question_id"])


def safety_false_positives(items: list[dict]) -> dict:
    validator = SQLSafetyValidator(max_rows=MAX_ROWS, max_sql_chars=10_000)
    blocked_sql = [
        {"question_id": x["question_id"], "reason": validator.validate(x["SQL"]).reason}
        for x in items if not validator.validate(x["SQL"]).is_safe
    ]
    refused = [
        {"question_id": x["question_id"], "matched": WRITE_INTENT.search(question_text(x)).group(0)}
        for x in items if WRITE_INTENT.search(question_text(x))
    ]
    return {"total": len(items), "gold_sql_blocked": blocked_sql, "questions_refused": refused}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "bird" / "MINIDEV")
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--per-level", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds per query execution")
    parser.add_argument("--schema", choices=("full", "retrieved"), default="full",
                        help="full: every table goes to the model; retrieved: keyword schema retrieval")
    parser.add_argument("--limit", type=int, default=0, help="only run the first N sampled items (smoke test)")
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "bird")
    args = parser.parse_args()

    items = json.loads((args.data_dir / "mini_dev_sqlite.json").read_text(encoding="utf-8"))
    chosen = sample(items, args.per_level, args.seed)
    if args.limit:
        chosen = chosen[: args.limit]

    generator = OllamaSQLGenerator(model=args.model)
    checker = SQLSafetyValidator(max_rows=MAX_ROWS, max_sql_chars=10_000)
    agents: dict[str, TextToSQLAgent] = {}
    connections: dict[str, sqlite3.Connection] = {}
    cases = []

    for number, item in enumerate(chosen, 1):
        db_id = item["db_id"]
        db_path = args.data_dir / "dev_databases" / db_id / f"{db_id}.sqlite"
        if db_id not in agents:
            agents[db_id] = TextToSQLAgent(
                EvalDatabase(f"sqlite:///{db_path}"), generator=generator, max_rows=MAX_ROWS,
                max_repairs=args.max_repairs, timeout_seconds=args.timeout, max_question_chars=4000,
                schema_retrieval=args.schema == "retrieved",
            )
            agents[db_id].validator.max_sql_chars = 10_000
            connections[db_id] = connect_readonly(db_path)
        connection = connections[db_id]

        try:
            gold = run_sql(connection, item["SQL"], args.timeout * 2)
        except Exception as exc:  # gold that cannot run in time is excluded, not counted as wrong
            cases.append({"question_id": item["question_id"], "difficulty": item["difficulty"],
                          "db_id": db_id, "excluded": f"gold SQL failed: {exc}"})
            continue

        calls_before = len(generator.calls)
        result = agents[db_id].run(question_text(item))
        calls = generator.calls[calls_before:]
        attempts = result.get("attempts") or []

        def correct(sql: str | None) -> bool:
            if not sql:
                return False
            checked = checker.validate(sql)
            if not checked.is_safe:
                return False
            try:
                return run_sql(connection, checked.sql, args.timeout) == gold
            except Exception:
                return False

        first_ok = bool(attempts) and attempts[0]["error"] is None and correct(attempts[0]["sql"])
        final_ok = result["status"] == "completed" and correct(result.get("sql"))
        case = {
            "question_id": item["question_id"], "difficulty": item["difficulty"], "db_id": db_id,
            "question": item["question"], "status": result["status"],
            "attempts": len(attempts), "repaired": len(attempts) > 1,
            "first_errors": [a["error"] for a in attempts if a["error"]],
            "ex_first": first_ok, "ex_final": final_ok,
            "pred_sql": result.get("sql", ""), "gold_sql": item["SQL"],
            "latency_ms": result["elapsed_ms"],
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "completion_tokens": sum(c["completion_tokens"] for c in calls),
        }
        cases.append(case)
        print(f"[{number}/{len(chosen)}] {item['question_id']} {item['difficulty']:<11} "
              f"first={'Y' if first_ok else '-'} final={'Y' if final_ok else '-'} "
              f"attempts={case['attempts']} {case['latency_ms']:.0f}ms", flush=True)

    scored = [c for c in cases if "excluded" not in c]
    by_level: dict[str, dict] = defaultdict(lambda: {"n": 0, "first": 0, "final": 0})
    for c in scored:
        for key in (c["difficulty"], "all"):
            by_level[key]["n"] += 1
            by_level[key]["first"] += c["ex_first"]
            by_level[key]["final"] += c["ex_final"]
    for stats in by_level.values():
        stats["ex_first"] = round(100 * stats["first"] / stats["n"], 1) if stats["n"] else 0.0
        stats["ex_final"] = round(100 * stats["final"] / stats["n"], 1) if stats["n"] else 0.0

    repaired = [c for c in scored if c["repaired"]]
    summary = {
        "model": args.model, "schema": args.schema, "seed": args.seed, "per_level": args.per_level, "max_repairs": args.max_repairs,
        "sampled": len(chosen), "scored": len(scored), "excluded": len(cases) - len(scored),
        "accuracy": {k: by_level[k] for k in (*LEVELS, "all") if k in by_level},
        "repair": {
            "triggered": len(repaired),
            "fixed": sum(1 for c in repaired if c["ex_final"] and not c["ex_first"]),
            "broke": sum(1 for c in scored if c["ex_first"] and not c["ex_final"]),
        },
        "latency_p50_ms": percentile([c["latency_ms"] for c in scored], 50),
        "latency_p95_ms": percentile([c["latency_ms"] for c in scored], 95),
        "avg_prompt_tokens": round(sum(c["prompt_tokens"] for c in scored) / max(1, len(scored))),
        "avg_completion_tokens": round(sum(c["completion_tokens"] for c in scored) / max(1, len(scored))),
        "safety_false_positives": safety_false_positives(items),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(
        json.dumps({"summary": summary, "cases": cases}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "RESULTS.md").write_text(render_markdown(summary, cases), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "safety_false_positives"}, ensure_ascii=False, indent=2))
    return 0


def render_markdown(summary: dict, cases: list[dict]) -> str:
    fp = summary["safety_false_positives"]
    acc = summary["accuracy"]
    lines = [
        "# BIRD Mini-Dev 评测结果",
        "",
        f"由 `python eval/run_bird_eval.py` 生成。模型 `{summary['model']}`（Ollama 本地，temperature 0，关闭思考），"
        f"从 BIRD Mini-Dev SQLite 版 500 条中按难度分层抽样（每档 {summary['per_level']} 条，seed {summary['seed']}），"
        f"Schema：{'全部表' if summary['schema'] == 'full' else '按问题关键词检索'}，使用题目自带的 evidence 提示。"
        "准确率为 BIRD 官方的执行准确率（EX）：预测 SQL 与标准 SQL 的结果集相同即为正确。",
        "",
        "## 执行准确率",
        "",
        f"| 难度 | 题数 | 不修复（首次生成） | 自修复（最多 {summary['max_repairs']} 次） | 提升 |",
        "| --- | --- | --- | --- | --- |",
    ]
    names = {"simple": "简单", "moderate": "中等", "challenging": "困难", "all": "**合计**"}
    for key, stats in acc.items():
        lines.append(f"| {names[key]} | {stats['n']} | {stats['ex_first']}% | {stats['ex_final']}% | "
                     f"{stats['ex_final'] - stats['ex_first']:+.1f} pp |")
    repair = summary["repair"]
    lines += [
        "",
        f"自修复：{repair['triggered']} 题触发（首次 SQL 被安全校验拦截或执行报错），修复后答对 {repair['fixed']} 题，"
        f"首次答对但修复后变错 {repair['broke']} 题。"
        "temperature 为 0 时首次生成的 SQL 与 `max_repairs=0` 的结果一致，所以“不修复”一列来自同一次运行。",
        "",
        f"延迟 P50 / P95：{summary['latency_p50_ms']} ms / {summary['latency_p95_ms']} ms；"
        f"平均每题 {summary['avg_prompt_tokens']} 个输入 token、{summary['avg_completion_tokens']} 个输出 token。"
        + (f" 另有 {summary['excluded']} 题标准 SQL 超时，已排除。" if summary["excluded"] else ""),
        "",
        "## 安全规则误伤（全部 500 条，不需要模型）",
        "",
        "| 检查 | 误伤 |",
        "| --- | --- |",
        f"| 标准 SQL 被安全校验拦截 | {len(fp['gold_sql_blocked'])}/{fp['total']} |",
        f"| 正常问题被判为写操作意图而拒绝 | {len(fp['questions_refused'])}/{fp['total']} |",
        "",
        "## 逐题明细",
        "",
        "| ID | 数据库 | 难度 | 状态 | 尝试次数 | 首次 | 最终 | 耗时 ms |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in cases:
        if "excluded" in c:
            lines.append(f"| {c['question_id']} | {c['db_id']} | {c['difficulty']} | 已排除 | | | | |")
            continue
        lines.append(f"| {c['question_id']} | {c['db_id']} | {c['difficulty']} | {c['status']} | {c['attempts']} | "
                     f"{'✅' if c['ex_first'] else '❌'} | {'✅' if c['ex_final'] else '❌'} | {c['latency_ms']:.0f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
