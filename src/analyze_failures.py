import json
import sys


def analyze(log_path: str = "logs/run_log_baseline.jsonl") -> None:
    with open(log_path, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]

    fails = [r for r in rows if not r["passed"]]
    print(f"Log: {log_path}")
    print(f"Total runs: {len(rows)} | Passed: {len(rows) - len(fails)} | Failed: {len(fails)}\n")

    for r in fails:
        print(f"--- Trial {r['trial']} | Q{r['question_id']:02d} ({r['category']}) ---")
        print(f"Question : {r['question']}")
        print(f"Status   : {r['status']} | Tokens: {r['total_tokens']}")
        print(f"SQL      : {r['sql_written']}")
        print(f"Expected : {r['expected']}")
        print(f"Answer   : {r['final_answer'][:180]}")
        if r["tool_calls"]:
            last_out = r["tool_calls"][-1]["output"]
            if isinstance(last_out, dict) and not last_out.get("ok", True):
                print(f"LastErr  : {last_out.get('error')}")
        print()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "logs/run_log_baseline.jsonl"
    analyze(path)