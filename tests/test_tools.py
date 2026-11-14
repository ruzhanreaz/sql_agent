import pytest
from src.db_builder import build_database
from src.tools import execute_sql, calculator, get_schema


@pytest.fixture
def sample_db(tmp_path):
    db_file = tmp_path / "test_store.db"
    build_database(str(db_file), seed=42)
    return str(db_file)


def test_execute_sql_valid_select(sample_db):
    res = execute_sql("SELECT COUNT(*) AS total FROM customers", db_path=sample_db)
    assert res["ok"] is True
    assert res["rows"] == [{"total": 30}]


def test_execute_sql_enforces_row_limit(sample_db):
    # order_items has ~250 rows, row_limit=10 should cap it
    res = execute_sql("SELECT * FROM order_items", db_path=sample_db, row_limit=10)
    assert res["ok"] is True
    assert len(res["rows"]) == 10
    assert res["truncated"] is True


@pytest.mark.parametrize(
    "bad_query",
    [
        "DROP TABLE customers",
        "DELETE FROM customers WHERE id = 1",
        "UPDATE customers SET city = 'Mars'",
        "INSERT INTO customers VALUES (99, 'Hack', 'X', '2025-01-01')",
        "ALTER TABLE customers ADD COLUMN age INT",
        "PRAGMA table_info(customers)",
        "SELECT * FROM customers; DROP TABLE customers;",
        "SELECT * FROM customers; SELECT * FROM products;",
    ],
)
def test_execute_sql_rejects_unsafe_queries(sample_db, bad_query):
    res = execute_sql(bad_query, db_path=sample_db)
    assert res["ok"] is False
    assert "error" in res


def test_execute_sql_returns_clear_error_on_bad_column(sample_db):
    res = execute_sql("SELECT non_existent_col FROM customers", db_path=sample_db)
    assert res["ok"] is False
    assert "no such column" in res["error"].lower()


def test_calculator_tool():
    res = calculator("(125.50 - 100.0) / 100.0 * 100")
    assert res["ok"] is True
    assert res["result"] == 25.5


def test_get_schema(sample_db):
    schema = get_schema(db_path=sample_db)
    assert "CREATE TABLE customers" in schema
    assert "order_items" in schema