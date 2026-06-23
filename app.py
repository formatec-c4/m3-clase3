import logging
import os

from flask import Flask, jsonify
import psycopg
from psycopg.rows import dict_row


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)


def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no esta configurada")
    return database_url


@app.get("/")
def index():
    app.logger.info("Solicitud recibida en /")
    return jsonify({"message": "Hola desde Docker con Python"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/db")
def db_info():
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT now() AS database_time, current_database() AS database_name")
            row = cur.fetchone()
    return jsonify(row)


@app.get("/visits")
def visits():
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS visits (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("INSERT INTO visits DEFAULT VALUES RETURNING id, created_at")
            visit = cur.fetchone()
            cur.execute("SELECT count(*) AS total FROM visits")
            total = cur.fetchone()["total"]
        conn.commit()

    return jsonify({"visit": visit, "total": total})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
