import os
import json
import psycopg2
from psycopg2 import sql
from getpass import getpass
from datetime import datetime


ALLOWED_TABLES = {
    "customers": ["id", "full_name", "email", "phone", "created_at"],
    "categories": ["id", "name"],
    "products": ["id", "name", "price", "stock", "category_id"],
    "orders": ["id", "customer_id", "order_date", "status"],
    "order_items": ["id", "order_id", "product_id", "quantity", "price"]
}


def log_info(msg: str):
    print(f"[INFO] {msg}")
    if os.getenv("LOG_FILE"):
        raw_log(msg)


def log_error(msg: str):
    print(f"[ERROR] {msg}", file=os.sys.stderr)
    if os.getenv("LOG_FILE"):
        raw_log(msg)


def raw_log(msg: str):
    path = os.getenv("LOG_FILE")
    if not path:
        return

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} {msg}\n")


def safe_error_message():
    return "Database operation failed. Please check input values or permissions."


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_connection_params(config, user, password):
    return {
        "host": config["host"],
        "port": config["port"],
        "database": config["database"],
        "user": user,
        "password": password
    }

def choose_table():
    print("\nAvailable tables:")
    for t in ALLOWED_TABLES:
        print(f"- {t}")

    table = input("Enter table name: ").strip()
    if table not in ALLOWED_TABLES:
        raise ValueError("Invalid table name")
    return table


def choose_column(table):
    print("\nAvailable columns:")
    for c in ALLOWED_TABLES[table]:
        print(f"- {c}")

    col = input("Enter column name: ").strip()
    if col not in ALLOWED_TABLES[table]:
        raise ValueError("Invalid column name")
    return col


def select_all(cur):
    table = choose_table()

    query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))
    cur.execute(query)

    rows = cur.fetchall()
    print("\nRESULT:")
    for r in rows:
        print(r)


def select_filter_one(cur):
    table = choose_table()
    column = choose_column(table)
    value = input("Enter filter value: ").strip()

    query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
        sql.Identifier(table),
        sql.Identifier(column)
    )

    cur.execute(query, (value,))
    rows = cur.fetchall()

    print("\nRESULT:")
    for r in rows:
        print(r)


def select_filter_two(cur):
    table = choose_table()

    col1 = choose_column(table)
    val1 = input(f"Enter value for {col1}: ").strip()

    col2 = choose_column(table)
    val2 = input(f"Enter value for {col2}: ").strip()

    query = sql.SQL("SELECT * FROM {} WHERE {} = %s AND {} = %s").format(
        sql.Identifier(table),
        sql.Identifier(col1),
        sql.Identifier(col2)
    )

    cur.execute(query, (val1, val2))
    rows = cur.fetchall()

    print("\nRESULT:")
    for r in rows:
        print(r)

def update_one_row(cur, conn):
    table = choose_table()
    row_id = input("Enter id of row to update: ").strip()

    updates = {}

    while True:
        col = input("Enter column to update (ENTER to finish): ").strip()
        if col == "":
            break

        if col not in ALLOWED_TABLES[table] or col == "id":
            print("Invalid column.")
            continue

        val = input(f"Enter new value for {col}: ").strip()
        updates[col] = val

    if not updates:
        print("No updates provided.")
        return

    set_clause = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(k)) for k in updates.keys()
    )

    query = sql.SQL("UPDATE {} SET {} WHERE id = %s").format(
        sql.Identifier(table),
        set_clause
    )

    values = list(updates.values()) + [row_id]

    cur.execute(query, values)
    conn.commit()

    print("Row updated successfully.")


def update_many_rows(cur, conn):
    table = choose_table()
    column = choose_column(table)

    new_value = input(f"Enter new value for {column}: ").strip()

    raw_values = input("Enter values for IN(...) separated by commas: ").strip()
    values = [v.strip() for v in raw_values.split(",") if v.strip()]

    if not values:
        print("No values provided.")
        return

    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in values)

    query = sql.SQL("UPDATE {} SET {} = %s WHERE {} IN ({})").format(
        sql.Identifier(table),
        sql.Identifier(column),
        sql.Identifier(column),
        placeholders
    )

    params = [new_value] + values

    cur.execute(query, params)
    conn.commit()

    print("Rows updated successfully.")



def insert_one_row(cur, conn):
    table = choose_table()

    columns = []
    values = []

    print("\nEnter values (skip id):")

    for col in ALLOWED_TABLES[table]:
        if col == "id":
            continue

        val = input(f"{col} (ENTER to skip): ").strip()
        if val == "":
            continue

        columns.append(col)
        values.append(val)

    if not columns:
        print("No values provided.")
        return

    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in values)
    )

    cur.execute(query, values)
    conn.commit()

    print("Row inserted successfully.")


def insert_order_with_items(cur, conn):
    print("\n=== Insert into multiple linked tables: orders + order_items ===")

    customer_id = input("Enter customer_id: ").strip()
    status = input("Enter status (NEW/PAID/CANCELLED): ").strip()

    cur.execute(
        "INSERT INTO orders (customer_id, status) VALUES (%s, %s) RETURNING id",
        (customer_id, status)
    )
    order_id = cur.fetchone()[0]

    print(f"Order created with id={order_id}")

    while True:
        product_id = input("Enter product_id (ENTER to finish): ").strip()
        if product_id == "":
            break

        quantity = input("Enter quantity: ").strip()
        price = input("Enter price: ").strip()

        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
            (order_id, product_id, quantity, price)
        )

    conn.commit()
    print("Order and items inserted successfully.")

def insert_many_rows(cur, conn):
    table = choose_table()
    count = int(input("How many rows to insert?: ").strip())

    if count <= 0:
        print("Invalid number.")
        return

    columns = [c for c in ALLOWED_TABLES[table] if c != "id"]

    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    )

    for i in range(count):
        print(f"\nRow {i+1}:")
        values = []
        for col in columns:
            val = input(f"{col}: ").strip()
            values.append(val)

        cur.execute(query, values)

    conn.commit()
    print("Multiple rows inserted successfully.")

def show_menu():
    print("\n=== MENU ===")
    print("1 - SELECT * FROM table (no filters)")
    print("2 - SELECT with filter (one column)")
    print("3 - SELECT with filter (two columns)")
    print("4 - UPDATE one row (by id)")
    print("5 - UPDATE many rows (IN list)")
    print("6 - INSERT one row into table")
    print("7 - INSERT into linked tables (orders + order_items)")
    print("8 - INSERT many rows into one table")
    print("0 - Exit")

def main():
    print("=== PostgreSQL CRUD console app ===")

    config_path = os.getenv("CONFIG_PATH", "config.json")
    config = load_config(config_path)

    user = input("Enter DB login: ").strip()
    password = getpass("Enter DB password: ")

    conn_params = build_connection_params(config, user, password)

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        log_info("Connection successful.")
        raw_log(f"CONNECT OK user={user}")

    except Exception as e:
        log_error("Connection failed.")
        raw_log(f"CONNECT FAIL user={user} err={repr(e)}")
        return

    while True:
        show_menu()
        choice = input("Choose action: ").strip()

        try:
            if choice == "1":
                select_all(cur)
            elif choice == "2":
                select_filter_one(cur)
            elif choice == "3":
                select_filter_two(cur)
            elif choice == "4":
                update_one_row(cur, conn)
            elif choice == "5":
                update_many_rows(cur, conn)
            elif choice == "6":
                insert_one_row(cur, conn)
            elif choice == "7":
                insert_order_with_items(cur, conn)
            elif choice == "8":
                insert_many_rows(cur, conn)
            elif choice == "0":
                break
            else:
                print("Unknown option.")

            raw_log(f"QUERY OK action={choice}")

        except Exception as e:
            log_error(safe_error_message())
            raw_log(f"QUERY FAIL action={choice} err={repr(e)}")

    cur.close()
    conn.close()
    log_info("Disconnected.")


if __name__ == "__main__":
    main()