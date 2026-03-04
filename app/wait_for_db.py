"""
Wait until the configured MySQL database accepts connections.
This avoids startup crashes when the app boots before MySQL is ready.
"""

import time

import pymysql

from app.config import settings

MAX_RETRIES = 30
SLEEP_SECONDS = 2


def wait_for_db() -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = pymysql.connect(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                connect_timeout=3,
            )
            conn.close()
            print("Database is ready.")
            return
        except Exception as exc:
            print(f"Waiting for database ({attempt}/{MAX_RETRIES}): {exc}")
            if attempt == MAX_RETRIES:
                raise SystemExit("Database connection failed after retries.")
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    wait_for_db()
