import json
import psycopg2
from getpass import getpass


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


def main():
    print("=== PostgreSQL version check app ===")

    config = load_config()

    user = input("Введите логин: ").strip()
    password = getpass("Введите пароль: ")

    conn_params = build_connection_params(config, user, password)

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        cur.execute("SELECT VERSION();")
        version = cur.fetchone()

        print("\nПодключение успешно!")
        print("Версия PostgreSQL:", version[0])

        cur.close()
        conn.close()

    except Exception as e:
        print("\nОшибка подключения:", e)


if __name__ == "__main__":
    main()