import json
import re
from src.agent import run_agent
from src.llm_client import ollama_chat


def extract_numbers(text: str) -> list[float]:
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def grade_answer(item: dict, result: dict) -> bool:
    if result["status"] != "ok":
        return False

    ans = result["final_answer"].lower()
    expected = item["expected"].lower()

    # For unanswerable questions, verify the agent refused rather than hallucinating numbers
    if not item["answerable"]:
        refusal_phrases = [
            "does not contain",
            "cannot answer",
            "no employee",
            "no payroll",
            "no rating",
            "no review",
            "not available",
            "no information",
            "no table",
            "no column",
        ]
        return any(p in ans for p in refusal_phrases)

    # Check key text labels if present (e.g., category, city, product name)
    for token in ["electronics", "books", "home", "clothing", "dhaka", "sylhet", "chittagong", "rajshahi", "khulna"]:
        if token in expected and token not in ans:
            return False

    prod_match = re.search(r"product_\d+", expected)
    if prod_match and prod_match.group(0) not in ans:
        return False

    # Check expected numbers appear within a 1% or 0.05 tolerance
    exp_nums = extract_numbers(expected)
    ans_nums = extract_numbers(ans)
    if not exp_nums:
        return expected in ans

    for en in exp_nums:
        if not any(abs(an - en) <= max(0.05, abs(en) * 0.01) for an in ans_nums):
            return False
    return True


def run_evaluation(
    questions_path: str = "data/questions.json",
    db_path: str = "data/store.db",
    log_path: str = "logs/run_log.jsonl",
    trials: int = 3,
    model: str = "qwen2.5:3b",
) -> None:
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    all_records = []
    per_question_passes = {q["id"]: [] for q in questions}

    for trial in range(1, trials + 1):
        print(f"\n--- Running Trial {trial}/{trials} ---")
        for q in questions:
            res = run_agent(
                question=q["question"],
                llm_call=lambda msgs, json_mode=True, t=trial: ollama_chat(
                    msgs, json_mode=json_mode, model=model, temperature=0.2, seed=100 + t
                ),
                db_path=db_path,
                max_steps=8,
                max_tokens=9000,
            )
            passed = grade_answer(q, res)
            per_question_passes[q["id"]].append(passed)

            record = {
                "trial": trial,
                "question_id": q["id"],
                "category": q["category"],
                "expected": q["expected"],
                "passed": passed,
                **res,
            }
            all_records.append(record)
            print(
                f"[T{trial} Q{q['id']:02d} | {q['category']}] "
                f"status={res['status']} passed={passed} tokens={res['total_tokens']} time={res['time_s']}s"
            )

    with open(log_path, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec) + "\n")

    total_runs = len(all_records)
    total_passed = sum(1 for r in all_records if r["passed"])
    pass_at_1 = (total_passed / total_runs) * 100

    all_3_passed = sum(1 for passes in per_question_passes.values() if all(passes))
    pass_pow_3 = (all_3_passed / len(questions)) * 100

    print("\n================ SUMMARY ================")
    print(f"Model: {model}")
    print(f"Total Runs: {total_runs} ({len(questions)} questions x {trials} trials)")
    print(f"pass@1: {total_passed}/{total_runs} ({pass_at_1:.1f}%)")
    print(f"pass^3: {all_3_passed}/{len(questions)} ({pass_pow_3:.1f}%)")
    print(f"Detailed log saved to: {log_path}")


if __name__ == "__main__":
    run_evaluation()