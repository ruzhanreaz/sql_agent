# Assignment 1: SQL Calculation Agent (`qwen2.5:3b`)

## Setup
- Python 3.10+ with `pytest` (`pip install pytest`)
- Local Ollama running `qwen2.5:3b`

## How to Run (4 Commands)
1. Run tests: `python -m pytest`
2. Build database: `python src/db_builder.py`
3. Generate questions: `python src/build_questions.py`
4. Run 3-trial evaluation: `python -m src.evaluate`