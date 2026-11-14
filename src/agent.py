import json
import time
from typing import Callable
from src.tools import calculator, execute_sql, generate_sql, get_schema


SYSTEM_PROMPT_TEMPLATE = """You are a precise data-analysis agent answering questions about a SQLite database.
You MUST NOT guess or compute numbers in your head. Use tools to query the database and compute math.

Database Schema:
{schema}

Available Tools:
1. generate_sql(sub_question): Drafts a SQLite SELECT query for a sub-question.
   Call with: {{"tool": "generate_sql", "args": {{"sub_question": "..."}}}}
2. execute_sql(query): Runs a read-only SELECT query and returns rows or a SQL error.
   Call with: {{"tool": "execute_sql", "args": {{"query": "SELECT ..."}}}}
3. calculator(expression): Evaluates a math expression accurately (e.g. "(150 - 120) / 120 * 100").
   Call with: {{"tool": "calculator", "args": {{"expression": "..."}}}}

Rules:
- Respond ONLY with a valid JSON object.
- To call a tool, respond with: {{"tool": "<tool_name>", "args": {{...}}}}
- Once you have verified the numbers from tool outputs, respond with: {{"final_answer": "<clear answer>"}}
- If the database schema does not contain the information needed to answer the question, do NOT make up numbers; respond with: {{"final_answer": "The database does not contain enough information to answer this question."}}
"""


def run_agent(
    question: str,
    llm_call: Callable,
    db_path: str = "data/store.db",
    max_steps: int = 8,
    max_tokens: int = 9000,
) -> dict:
    start_time = time.perf_counter()
    schema = get_schema(db_path=db_path)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(schema=schema)},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []
    sql_queries = []
    total_tokens = 0
    steps = 0

    while steps < max_steps:
        if total_tokens >= max_tokens:
            return _build_result(
                question, tool_calls_log, sql_queries, "", "budget_cap", total_tokens, start_time
            )

        try:
            resp = llm_call(messages, json_mode=True)
        except Exception as exc:
            return _build_result(
                question, tool_calls_log, sql_queries, f"LLM Error: {exc}", "error", total_tokens, start_time
            )

        total_tokens += resp.get("prompt_tokens", 0) + resp.get("output_tokens", 0)
        if total_tokens >= max_tokens:
            return _build_result(
                question, tool_calls_log, sql_queries, "", "budget_cap", total_tokens, start_time
            )

        raw_content = resp["content"]
        messages.append({"role": "assistant", "content": raw_content})

        try:
            action = json.loads(raw_content)
        except json.JSONDecodeError:
            messages.append({
                "role": "user",
                "content": "Invalid JSON. Respond ONLY with {\"tool\": ..., \"args\": ...} or {\"final_answer\": ...}.",
            })
            steps += 1
            continue

        if "final_answer" in action:
            return _build_result(
                question,
                tool_calls_log,
                sql_queries,
                str(action["final_answer"]),
                "ok",
                total_tokens,
                start_time,
            )

        tool_name = action.get("tool")
        args = action.get("args", {})
        steps += 1

        if tool_name == "generate_sql":
            sub_q = args.get("sub_question") or args.get("question") or question
            out = generate_sql(
                sub_q,
                llm_call=lambda msgs: llm_call(msgs, json_mode=False),
                db_path=db_path,
            )
            total_tokens += out.get("tokens", 0)
            if out.get("sql"):
                sql_queries.append(out["sql"])
        elif tool_name == "execute_sql":
            query = (args.get("query") or args.get("sql") or args.get("statement") or "").strip().strip('"')
            if query:
                sql_queries.append(query)
            out = execute_sql(query, db_path=db_path)
        elif tool_name == "calculator":
            expr = args.get("expression") or args.get("expr") or ""
            out = calculator(expr)
        else:
            out = {"ok": False, "error": f"Unknown tool: {tool_name}"}

        tool_calls_log.append({"step": steps, "tool": tool_name, "args": args, "output": out})
        messages.append({
            "role": "user",
            "content": f"Tool `{tool_name}` result:\n{json.dumps(out)}",
        })

    return _build_result(
        question, tool_calls_log, sql_queries, "", "step_cap", total_tokens, start_time
    )


def _build_result(
    question: str,
    tool_calls: list,
    sql_queries: list,
    final_answer: str,
    status: str,
    total_tokens: int,
    start_time: float,
) -> dict:
    return {
        "question": question,
        "tool_calls": tool_calls,
        "sql_written": sql_queries,
        "final_answer": final_answer,
        "status": status,
        "total_tokens": total_tokens,
        "time_s": round(time.perf_counter() - start_time, 3),
    }