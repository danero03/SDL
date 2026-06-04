import os
import sys
import json
import time
from datetime import datetime
import psycopg2
import hvac


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


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def get_db_credentials():
    """
    Получает логин и пароль из Vault через AppRole
    """
    vault_addr = os.getenv("VAULT_ADDR")
    role_id = os.getenv("VAULT_ROLE_ID")
    secret_id = os.getenv("VAULT_SECRET_ID")
    secret_path = os.getenv("VAULT_SECRET_PATH", "db-creds")
    mount_point = os.getenv("VAULT_KV_MOUNT", "secret")

    if not vault_addr or not role_id or not secret_id:
        raise RuntimeError(
            "Задайте VAULT_ADDR, VAULT_ROLE_ID, VAULT_SECRET_ID "
            "(получите из Vault: vault read .../role-id и vault write -f .../secret-id)"
        )

    client = hvac.Client(url=vault_addr)

    try:
        # Авторизация через AppRole
        auth_response = client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка авторизации в Vault: {e}")

    client.token = auth_response["auth"]["client_token"]

    try:
        # Чтение секрета (KV v2)
        read_response = client.secrets.kv.v2.read_secret_version(
            path=secret_path,
            mount_point=mount_point,
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения секрета: {e}")

    data = read_response["data"]["data"]

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise RuntimeError("Секрет не содержит username/password")

    return username, password


def build_connection_params(config: dict, user: str, password: str) -> dict:
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

    interval = get_interval_seconds()
    log(f"Интервал опроса: {interval} секунд")

    while True:
        start = time.time()

        try:
            # Получаем секрет перед каждым подключением
            db_user, db_password = get_db_credentials()

            conn_params = build_connection_params(config, db_user, db_password)

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