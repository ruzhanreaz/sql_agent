import json
import sqlite3


def q(conn, sql):
    return conn.execute(sql).fetchone()[0]


def generate_questions(db_path: str = "data/store.db", out_path: str = "data/questions.json") -> None:
    conn = sqlite3.connect(db_path)

    # Pre-compute ground-truth values using our own SQL
    c_total = q(conn, "SELECT COUNT(*) FROM customers")
    p_total = q(conn, "SELECT COUNT(*) FROM products")
    o_cancelled = q(conn, "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'")

    rev_cust_12 = round(
        q(
            conn,
            """
            SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0)
            FROM orders o JOIN order_items oi ON o.id = oi.order_id
            WHERE o.customer_id = 12
            """,
        ),
        2,
    )
    orders_dhaka = q(
        conn,
        """
        SELECT COUNT(*) FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE c.city = 'Dhaka'
        """,
    )
    qty_prod_5 = q(
        conn,
        "SELECT COALESCE(SUM(quantity), 0) FROM order_items WHERE product_id = 5",
    )

    top_cat_row = conn.execute(
        """
        SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS rev
        FROM order_items oi JOIN products p ON oi.product_id = p.id
        GROUP BY p.category ORDER BY rev DESC LIMIT 1
        """
    ).fetchone()

    top_city_row = conn.execute(
        """
        SELECT city, COUNT(*) AS cnt FROM customers
        GROUP BY city ORDER BY cnt DESC LIMIT 1
        """
    ).fetchone()

    top_prod_row = conn.execute(
        """
        SELECT p.name, SUM(oi.quantity) AS units
        FROM order_items oi JOIN products p ON oi.product_id = p.id
        GROUP BY p.id ORDER BY units DESC LIMIT 1
        """
    ).fetchone()

    # Calculation questions
    order_totals = [
        r[0]
        for r in conn.execute(
            "SELECT SUM(quantity * unit_price) FROM order_items GROUP BY order_id"
        ).fetchall()
    ]
    avg_order = round(sum(order_totals) / len(order_totals), 2)
    min_order = round(min(order_totals), 2)
    pct_above_min = round(((avg_order - min_order) / min_order) * 100, 2)

    total_rev = round(q(conn, "SELECT SUM(quantity * unit_price) FROM order_items"), 2)
    completed_rev = round(
        q(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price)
            FROM order_items oi JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed'
            """,
        ),
        2,
    )
    completed_share = round((completed_rev / total_rev) * 100, 2)

    avg_prod_price = round(q(conn, "SELECT AVG(price) FROM products"), 2)

    # Multi-tool questions (e.g., query 1 + query 2 + calculator)
    rev_dhaka = round(
        q(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price)
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN customers c ON o.customer_id = c.id
            WHERE c.city = 'Dhaka'
            """,
        ),
        2,
    )
    rev_sylhet = round(
        q(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price)
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN customers c ON o.customer_id = c.id
            WHERE c.city = 'Sylhet'
            """,
        ),
        2,
    )
    dhaka_vs_sylhet_diff = round(rev_dhaka - rev_sylhet, 2)

    rev_elec = round(
        q(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price)
            FROM order_items oi JOIN products p ON oi.product_id = p.id
            WHERE p.category = 'Electronics'
            """,
        ),
        2,
    )
    rev_books = round(
        q(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price)
            FROM order_items oi JOIN products p ON oi.product_id = p.id
            WHERE p.category = 'Books'
            """,
        ),
        2,
    )
    elec_over_books_pct = round(((rev_elec - rev_books) / rev_books) * 100, 2)

    questions = [
        # 1-3: Simple
        {"id": 1, "category": "simple", "question": "How many customers are there?", "expected": str(c_total), "answerable": True},
        {"id": 2, "category": "simple", "question": "How many products are listed in the products table?", "expected": str(p_total), "answerable": True},
        {"id": 3, "category": "simple", "question": "How many orders have the status 'cancelled'?", "expected": str(o_cancelled), "answerable": True},
        # 4-6: Joins
        {"id": 4, "category": "join", "question": "What is the total revenue (quantity * unit_price) for customer 12?", "expected": str(rev_cust_12), "answerable": True},
        {"id": 5, "category": "join", "question": "How many total orders were placed by customers living in Dhaka?", "expected": str(orders_dhaka), "answerable": True},
        {"id": 6, "category": "join", "question": "What is the total quantity of units sold for product id 5?", "expected": str(qty_prod_5), "answerable": True},
        # 7-9: Grouping
        {"id": 7, "category": "grouping", "question": "Which product category earned the most total revenue, and how much did it earn?", "expected": f"{top_cat_row[0]} ({top_cat_row[1]})", "answerable": True},
        {"id": 8, "category": "grouping", "question": "Which city has the highest number of customers, and how many customers are there?", "expected": f"{top_city_row[0]} ({top_city_row[1]})", "answerable": True},
        {"id": 9, "category": "grouping", "question": "Which product name sold the highest total quantity of units?", "expected": f"{top_prod_row[0]} ({top_prod_row[1]})", "answerable": True},
        # 10-12: Calculation
        {"id": 10, "category": "calculation", "question": "What is the average order value, and by what percentage is it above the minimum order value?", "expected": f"avg={avg_order}, min={min_order}, pct_above={pct_above_min}%", "answerable": True},
        {"id": 11, "category": "calculation", "question": "What percentage of total revenue comes from 'completed' orders?", "expected": f"{completed_share}% ({completed_rev} / {total_rev})", "answerable": True},
        {"id": 12, "category": "calculation", "question": "What is the average price of all products in the catalog?", "expected": str(avg_prod_price), "answerable": True},
        # 13-14: Multi-tool (2+ SQL queries + calculator)
        {"id": 13, "category": "multi_tool", "question": "Find the total revenue from Dhaka customers and the total revenue from Sylhet customers separately, then use the calculator to find the exact difference (Dhaka minus Sylhet).", "expected": f"Dhaka={rev_dhaka}, Sylhet={rev_sylhet}, diff={dhaka_vs_sylhet_diff}", "answerable": True},
        {"id": 14, "category": "multi_tool", "question": "Query the total revenue for Electronics and the total revenue for Books separately, then use the calculator to find by what percentage Electronics revenue is higher than Books revenue.", "expected": f"Electronics={rev_elec}, Books={rev_books}, pct={elec_over_books_pct}%", "answerable": True},
        # 15-16: Unanswerable
        {"id": 15, "category": "unanswerable", "question": "What was the total employee payroll expense in March 2025?", "expected": "Cannot answer (no employee/payroll table in database)", "answerable": False},
        {"id": 16, "category": "unanswerable", "question": "Which product received the lowest average customer star rating?", "expected": "Cannot answer (no ratings/reviews column or table in database)", "answerable": False},
    ]

    conn.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2)
    print(f"Saved {len(questions)} verified questions to {out_path}")


if __name__ == "__main__":
    generate_questions()