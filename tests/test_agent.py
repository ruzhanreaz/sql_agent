import json
import pytest
from src.db_builder import build_database
from src.agent import run_agent


@pytest.fixture
def sample_db(tmp_path):
    db_file = tmp_path / "test_store.db"
    build_database(str(db_file), seed=42)
    return str(db_file)


def test_agent_completes_with_tools(sample_db):
    # Simulated 3-step sequence: generate_sql -> execute_sql -> final_answer
    responses = [
        {
            "content": json.dumps({"tool": "generate_sql", "args": {"sub_question": "count customers"}}),
            "prompt_tokens": 100,
            "output_tokens": 20,
        },
        {
            "content": "SELECT COUNT(*) AS cnt FROM customers",  # returned to generate_sql's internal call
            "prompt_tokens": 80,
            "output_tokens": 10,
        },
        {
            "content": json.dumps({"tool": "execute_sql", "args": {"query": "SELECT COUNT(*) AS cnt FROM customers"}}),
            "prompt_tokens": 150,
            "output_tokens": 25,
        },
        {
            "content": json.dumps({"final_answer": "There are 30 customers."}),
            "prompt_tokens": 180,
            "output_tokens": 15,
        },
    ]
    call_idx = {"i": 0}

    def fake_llm(messages, json_mode=True):
        resp = responses[call_idx["i"]]
        call_idx["i"] += 1
        return resp

    result = run_agent(
        question="How many customers are there?",
        llm_call=fake_llm,
        db_path=sample_db,
        max_steps=6,
        max_tokens=5000,
    )

    assert result["status"] == "ok"
    assert "30" in result["final_answer"]
    assert len(result["tool_calls"]) == 2
    assert result["total_tokens"] == 580


def test_agent_hits_step_cap(sample_db):
    # Model keeps calling calculator forever
    def infinite_tool_llm(messages, json_mode=True):
        return {
            "content": json.dumps({"tool": "calculator", "args": {"expression": "1 + 1"}}),
            "prompt_tokens": 50,
            "output_tokens": 10,
        }

    result = run_agent(
        question="Loop forever",
        llm_call=infinite_tool_llm,
        db_path=sample_db,
        max_steps=3,
        max_tokens=10000,
    )

    assert result["status"] == "step_cap"
    assert len(result["tool_calls"]) == 3


def test_agent_hits_budget_cap(sample_db):
    def expensive_llm(messages, json_mode=True):
        return {
            "content": json.dumps({"tool": "calculator", "args": {"expression": "2 * 2"}}),
            "prompt_tokens": 600,
            "output_tokens": 100,
        }

    result = run_agent(
        question="Expensive loop",
        llm_call=expensive_llm,
        db_path=sample_db,
        max_steps=10,
        max_tokens=1000,
    )

    assert result["status"] == "budget_cap"


def test_agent_recovers_from_sql_error(sample_db):
    # Step 1: bad column -> receives SQL error -> Step 2: fixes column -> Step 3: answers
    responses = [
        {
            "content": json.dumps({"tool": "execute_sql", "args": {"query": "SELECT bad_col FROM customers"}}),
            "prompt_tokens": 100,
            "output_tokens": 20,
        },
        {
            "content": json.dumps({"tool": "execute_sql", "args": {"query": "SELECT COUNT(*) AS c FROM customers"}}),
            "prompt_tokens": 140,
            "output_tokens": 20,
        },
        {
            "content": json.dumps({"final_answer": "Total customers: 30"}),
            "prompt_tokens": 160,
            "output_tokens": 15,
        },
    ]
    idx = {"i": 0}

    def recovery_llm(messages, json_mode=True):
        resp = responses[idx["i"]]
        idx["i"] += 1
        return resp

    result = run_agent("How many customers?", llm_call=recovery_llm, db_path=sample_db)
    assert result["status"] == "ok"
    assert "30" in result["final_answer"]
    assert "no such column" in result["tool_calls"][0]["output"]["error"].lower()