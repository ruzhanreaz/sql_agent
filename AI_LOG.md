# AI Assistant Usage Log
- **What it wrote:** Assisted in scaffolding `src/db_builder.py`, `src/tools.py`, `src/agent.py`, `src/evaluate.py`, and documentation templates.
- **Which test proves it:** Verified by 19 unit tests (`tests/test_db.py`, `tests/test_tools.py`, `tests/test_agent.py`) and the 48-run SQL-verified benchmark in `logs/run_log.jsonl`.
- **What I reviewed:** Reviewed read-only SQLite safety guards, step/token loop caps, ground-truth SQL queries, and failure logs across all three evaluation runs.