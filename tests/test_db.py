import sqlite3
from src.db_builder import build_database


def test_database_schema_and_row_counts(tmp_path):
    db_file = tmp_path / "test_store.db"
    build_database(str(db_file), seed=42)

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # 1. Check at least 3 related tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}
    expected_tables = {"customers", "products", "orders", "order_items"}
    assert expected_tables.issubset(tables)

    # 2. Check biggest table has >= 100 rows
    counts = {}
    for table in expected_tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cur.fetchone()[0]

    assert max(counts.values()) >= 100
    assert all(c > 0 for c in counts.values())
    conn.close()


def test_database_is_deterministic(tmp_path):
    db1 = tmp_path / "db1.db"
    db2 = tmp_path / "db2.db"

    build_database(str(db1), seed=42)
    build_database(str(db2), seed=42)

    conn1 = sqlite3.connect(db1)
    conn2 = sqlite3.connect(db2)

    rows1 = conn1.execute("SELECT * FROM order_items ORDER BY id").fetchall()
    rows2 = conn2.execute("SELECT * FROM order_items ORDER BY id").fetchall()

    assert rows1 == rows2
    conn1.close()
    conn2.close()