import os
import random
import sqlite3
from datetime import datetime, timedelta


def build_database(db_path: str = "data/store.db", seed: int = 42) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    rng = random.Random(seed)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )

    cities = ["Dhaka", "Chittagong", "Sylhet", "Rajshahi", "Khulna"]
    base_date = datetime(2025, 1, 1)

    # 1. Insert 30 customers
    customers = []
    for cid in range(1, 31):
        name = f"Customer_{cid:02d}"
        city = rng.choice(cities)
        signup = (base_date + timedelta(days=rng.randint(0, 180))).strftime("%Y-%m-%d")
        customers.append((cid, name, city, signup))
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)

    # 2. Insert 20 products
    categories = ["Electronics", "Books", "Home", "Clothing"]
    products = []
    for pid in range(1, 21):
        name = f"Product_{pid:02d}"
        cat = categories[(pid - 1) % len(categories)]
        price = round(rng.uniform(10.0, 250.0), 2)
        products.append((pid, name, cat, price))
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)

    # 3. Insert 120 orders
    statuses = ["completed", "completed", "completed", "shipped", "cancelled"]
    orders = []
    for oid in range(1, 121):
        cid = rng.randint(1, 30)
        odate = (base_date + timedelta(days=rng.randint(181, 360))).strftime("%Y-%m-%d")
        status = rng.choice(statuses)
        orders.append((oid, cid, odate, status))
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)

    # 4. Insert ~250 order_items (ensures > 100 rows in largest table)
    order_items = []
    item_id = 1
    product_price_map = {p[0]: p[3] for p in products}
    for oid in range(1, 121):
        num_items = rng.randint(1, 3)
        chosen_products = rng.sample(range(1, 21), num_items)
        for pid in chosen_products:
            qty = rng.randint(1, 5)
            unit_price = product_price_map[pid]
            order_items.append((item_id, oid, pid, qty, unit_price))
            item_id += 1
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    build_database("data/store.db", seed=42)
    print("Database built at data/store.db")