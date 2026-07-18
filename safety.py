"""SQL safety rules used before every database execution."""

from __future__ import annotations

import re
from dataclasses import dataclass


FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
}


@dataclass(frozen=True)
class ValidationResult:
    is_safe: bool
    sql: str
    reason: str | None = None


class SQLSafetyValidator:
    """Allow only one bounded SELECT/CTE statement."""

    def __init__(self, max_rows: int = 200) -> None:
        self.max_rows = max_rows

    def validate(self, sql: str) -> ValidationResult:
        normalized = self._normalize(sql)
        if not normalized:
            return ValidationResult(False, "", "SQL 为空")

        if ";" in normalized.rstrip(";"):
            return ValidationResult(False, normalized, "仅允许执行一条 SQL")

        statement = normalized.rstrip(";").strip()
        upper = statement.upper()
        if not (upper.startswith("SELECT ") or upper.startswith("WITH ")):
            return ValidationResult(False, statement, "仅允许 SELECT 或 WITH 查询")

        found = sorted(
            keyword
            for keyword in FORBIDDEN_KEYWORDS
            if re.search(rf"\b{keyword}\b", upper)
        )
        if found:
            return ValidationResult(
                False,
                statement,
                f"检测到禁止的写操作或管理命令：{', '.join(found)}",
            )

        return ValidationResult(True, self._bound_rows(statement))

    def _normalize(self, sql: str) -> str:
        without_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
        without_line_comments = re.sub(r"--[^\n]*", " ", without_block_comments)
        return re.sub(r"\s+", " ", without_line_comments).strip()

    def _bound_rows(self, sql: str) -> str:
        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", sql, flags=re.I)
        if not limit_match:
            return f"{sql} LIMIT {self.max_rows}"

        requested = int(limit_match.group(1))
        if requested <= self.max_rows:
            return sql
        start, end = limit_match.span(1)
        return f"{sql[:start]}{self.max_rows}{sql[end:]}"

