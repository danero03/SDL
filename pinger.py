import os
import sys
import json
import time
from datetime import datetime

import psycopg2


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


LOG_FILE_PATH = os.getenv("LOG_FILE")


def log(message: str, error: bool = False) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    level = "ERROR" if error else "INFO"
    line = f"[{ts}] {level} {message}"

    stream = sys.stderr if error else sys.stdout
    print(line, file=stream, flush=True)

    if LOG_FILE_PATH:
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[{ts}] ERROR Ошибка записи в лог-файл: {e}",
                  file=sys.stderr, flush=True)


def get_interval_seconds() -> int:
    raw = os.getenv("DB_PING_INTERVAL", "300")
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        log(f"Некорректное значение DB_PING_INTERVAL={raw!r}, "
            f"использую 300 секунд по умолчанию", error=True)
        return 300


def build_connection_params(config: dict, user: str, password: str) -> dict:
    """Безопасно объединяем данные из файла и env (user/password)."""
    return {
        "host": config["host"],
        "port": config["port"],
        "database": config["database"],
        "user": user,
        "password": password,
        "connect_timeout": 10,
    }


def main() -> None:
    log("Старт приложения pinger")

    config_path = os.getenv("DB_CONFIG_PATH", "config.json")
    try:
        config = load_config(config_path)
    except Exception as e:
        log(f"Не удалось прочитать конфиг {config_path}: {e}", error=True)
        sys.exit(1)

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not db_user or not db_password:
        log("Переменные окружения DB_USER и/или DB_PASSWORD не заданы", error=True)
        sys.exit(1)

    interval = get_interval_seconds()
    log(f"Интервал опроса: {interval} секунд")

    conn_params = build_connection_params(config, db_user, db_password)

    while True:
        start = time.time()
        try:
            with psycopg2.connect(**conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT VERSION();")
                    row = cur.fetchone()

            if not row:
                log("Необычный ответ: SELECT VERSION() вернул пустой результат")
            else:
                version = row[0]
                if isinstance(version, str) and version.startswith("PostgreSQL"):
                    log(f"Успешное подключение. Версия БД: {version}")
                else:
                    log(f"Необычный ответ на SELECT VERSION(): {version!r}")

        except Exception as e:
            log(f"Ошибка подключения или выполнения запроса: {e}", error=True)

        elapsed = time.time() - start
        sleep_for = max(0, interval - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
