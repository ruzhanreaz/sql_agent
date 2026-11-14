import ast
import operator
import os
import re
import sqlite3
from typing import Callable, Optional


FORBIDDEN_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|PRAGMA|ATTACH|DETACH|REPLACE|CREATE|VACUUM)\b",
    re.IGNORECASE,
)


def get_schema(db_path: str = "data/store.db") -> str:
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name;"
        )
        rows = cur.fetchall()
        return "\n\n".join(row[0] + ";" for row in rows)
    finally:
        conn.close()


def execute_sql(
    query: str, db_path: str = "data/store.db", row_limit: int = 50
) -> dict:
    if not query or not isinstance(query, str):
        return {"ok": False, "error": "Query must be a non-empty string."}

    cleaned = query.strip()
    # Allow a single trailing semicolon, then forbid any other semicolons
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    if ";" in cleaned:
        return {"ok": False, "error": "Safety error: multiple SQL statements are not allowed."}

    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        return {"ok": False, "error": "Safety error: only SELECT queries are allowed."}

    if FORBIDDEN_KEYWORDS.search(cleaned):
        return {"ok": False, "error": "Safety error: forbidden SQL keyword detected."}

    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(cleaned)
        fetched = cur.fetchmany(row_limit + 1)
        truncated = len(fetched) > row_limit
        rows = [dict(r) for r in fetched[:row_limit]]
        conn.close()
        return {
            "ok": True,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }
    except sqlite3.Error as exc:
        return {"ok": False, "error": f"SQL Error: {exc}"}


# Safe math evaluator for the calculator tool
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported mathematical expression")


def calculator(expression: str) -> dict:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        val = _eval_node(tree.body)
        return {"ok": True, "result": round(float(val), 6)}
    except Exception as exc:
        return {"ok": False, "error": f"Calculator error: {exc}"}


def generate_sql(
    sub_question: str,
    llm_call: Callable[[list[dict]], dict],
    db_path: str = "data/store.db",
) -> dict:
    """SQL generation tool: uses the schema + LLM call to draft a SELECT query."""
    schema = get_schema(db_path=db_path)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a SQLite SQL generator. Output ONLY a single valid SQLite SELECT "
                "query with no markdown fences, no explanation, and no semicolon.\n\n"
                f"Database Schema:\n{schema}"
            ),
        },
        {"role": "user", "content": sub_question},
    ]
    resp = llm_call(messages)
    sql = resp["content"].strip()
    # Strip markdown code fences if the small model adds them
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()
    return {
        "ok": True,
        "sql": sql,
        "tokens": resp.get("prompt_tokens", 0) + resp.get("output_tokens", 0),
    }