"""SQL safety rules applied to every statement before it reaches the database."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Statements and clauses that change data, schema, permissions or the connection.
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
    "REINDEX", "ANALYZE", "COPY", "CALL", "EXEC", "EXECUTE", "INTO", "LOCK", "SET",
}

# Functions that read or write files, load native code, or exist mainly to stall the server.
FORBIDDEN_FUNCTIONS = {
    "load_extension", "readfile", "writefile", "edit", "fts3_tokenizer",
    "randomblob", "zeroblob",                                   # SQLite
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
    "lo_import", "lo_export", "dblink", "dblink_exec",           # PostgreSQL
    "sleep", "benchmark", "load_file",                           # MySQL
}

_STRING_OR_QUOTED = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|`[^`]*`|\[[^\]]*\]")


@dataclass(frozen=True)
class ValidationResult:
    is_safe: bool
    sql: str
    reason: str | None = None


class SQLSafetyValidator:
    """Allow exactly one SELECT/WITH statement, and bound how many rows it can return."""

    def __init__(self, max_rows: int = 200, max_sql_chars: int = 2000) -> None:
        self.max_rows = max_rows
        self.max_sql_chars = max_sql_chars

    def validate(self, sql: str) -> ValidationResult:
        if len(sql or "") > self.max_sql_chars:
            return ValidationResult(False, "", f"SQL 超过 {self.max_sql_chars} 个字符")
        statement = self._strip_comments(sql or "").strip().rstrip(";").strip()
        if not statement:
            return ValidationResult(False, "", "SQL 为空")

        # Keywords and semicolons inside string literals or quoted names are data, not SQL.
        code = _STRING_OR_QUOTED.sub(" '' ", statement)
        if ";" in code:
            return ValidationResult(False, statement, "仅允许执行一条 SQL")
        upper = code.upper()
        if not re.match(r"(SELECT|WITH)\b", upper):
            return ValidationResult(False, statement, "仅允许 SELECT 或 WITH 查询")

        keywords = sorted(k for k in FORBIDDEN_KEYWORDS if re.search(rf"\b{k}\b", upper))
        if re.search(r"\bREPLACE\s+INTO\b", upper):
            keywords.append("REPLACE INTO")
        if keywords:
            return ValidationResult(False, statement, f"检测到禁止的写操作或管理命令：{', '.join(keywords)}")

        functions = sorted(f for f in FORBIDDEN_FUNCTIONS if re.search(rf"\b{f}\s*\(", code, flags=re.I))
        if functions:
            return ValidationResult(False, statement, f"检测到禁止的数据库函数：{', '.join(functions)}")

        return ValidationResult(True, self._bound_rows(statement))

    @staticmethod
    def _strip_comments(sql: str) -> str:
        # Comments are removed outside string literals only.
        parts, last = [], 0
        for match in _STRING_OR_QUOTED.finditer(sql):
            parts.append(re.sub(r"/\*.*?\*/|--[^\n]*", " ", sql[last:match.start()], flags=re.S))
            parts.append(match.group(0))
            last = match.end()
        parts.append(re.sub(r"/\*.*?\*/|--[^\n]*", " ", sql[last:], flags=re.S))
        return re.sub(r"\s+", " ", "".join(parts))

    def _bound_rows(self, sql: str) -> str:
        # Wrapping applies the limit to the outer result, whatever LIMITs the inner query or its CTEs use.
        return f"SELECT * FROM ({sql}) AS bounded_result LIMIT {self.max_rows}"
