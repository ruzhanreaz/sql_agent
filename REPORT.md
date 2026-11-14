# Assignment 1 Report: SQL Calculation Agent

## 1. Architecture
- **Model:** `qwen2.5:3b` via Ollama (`/api/chat`, `format="json"`, `temperature=0.2`, seeds `101-103`).
- **Database:** SQLite (`data/store.db`, `seed=42`) with 4 tables: `customers` (30), `products` (20), `orders` (120), and `order_items` (240+ rows).
- **Custom Loop (`src/agent.py`):** Written without frameworks; enforces `max_steps=8`, `max_tokens=9000`, JSON action parsing, and SQL error feedback so the model can retry.
- **Tools (`src/tools.py`):**
  1. `generate_sql(sub_question)`: Calls `qwen2.5:3b` with the `CREATE TABLE` schema to draft a SQLite `SELECT` query.
  2. `execute_sql(query)`: Opens SQLite in read-only URI mode (`mode=ro`), blocks non-`SELECT` keywords and `;` multi-statements, and enforces a 50-row limit.
  3. `calculator(expression)` *(Bonus)*: Safe Python `ast` math evaluator so arithmetic is computed by a tool rather than the model.
- **Data Flow:** `User Question -> Custom Agent Loop (step & token caps) -> [generate_sql | execute_sql | calculator] -> Tool Output / SQL Error -> Final Answer`

## 2. Evaluation Results (`pass@1` and `pass^3`)
Evaluated on 16 questions x 3 trials = 48 runs against SQL-verified ground-truth answers:

| Version | `pass@1` | `pass^3` | Notes |
| :--- | :--- | :--- | :--- |
| **v1 (Baseline: concise prompt, 6k cap)** | **32/48 (66.7%)** | **10/16 (62.5%)** | Strong on simple, join, and unanswerable queries |
| **v2 (Verbose negative rules added)** | 25/48 (52.1%) | 7/16 (43.8%) | Regressed: prompt bloat & refusal failures |
| **v3 (Arg-key normalization + 9k cap)** | **32/48 (66.7%)** | **10/16 (62.5%)** | Fixed `sql` vs `query` key mismatches |

## 3. Three Most Common Failure Types
1. **Hallucinated Column Ownership & Premature Refusal (Q11):**
   - *Example (Trial 1, Q11):* Wrote `SUM(o.quantity * oi.unit_price)` instead of `oi.quantity`, received `SQL Error: no such column: o.quantity`, and falsely claimed the database lacked `quantity` instead of fixing the alias.
2. **Mental Arithmetic Instead of Calling `calculator` (Q10):**
   - *Example (Trial 1, Q10):* SQL returned `avg=841.36` and `min=54.28`, but the model skipped `calculator` and guessed `154.3%` in its head instead of `1450.04%`.
3. **Over-Nested `UNION` Queries & Token Budget Caps (Q13, Q14):**
   - *Example (Trial 3, Q13):* Built a nested `UNION ALL` with an invalid `GROUP BY` aggregate instead of two simple queries, repeating errors until hitting `budget_cap`.

## 4. Before vs. After Change
- **What did not work:** Adding 5 long negative rules (`NEVER use UNION`, `Do NOT claim the database lacks information...`) dropped `pass@1` from **66.7% to 52.1%** (`pass^3`: **62.5% to 43.8%**) because the model looped on unanswerable Q16 and hit `budget_cap`.
- **What improved reliability:** Restoring the concise prompt while normalizing `execute_sql` argument keys (`query`/`sql`/`statement`) and increasing `max_tokens` from 6,000 to 9,000 eliminated empty-query argument errors and restored **66.7% `pass@1` (`32/48`)** and **62.5% `pass^3` (`10/16`)**.