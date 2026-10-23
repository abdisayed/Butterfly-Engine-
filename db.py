import os
import json
import pandas as pd
import mysql.connector

REQUIRED = ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]


def get_connection():
    missing = [k for k in REQUIRED if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing .env variables: {', '.join(missing)}")
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )


def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assumptions_json JSON NOT NULL,
                strategies_json JSON NOT NULL,
                summary_json JSON NOT NULL
            )
        """)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def save_run(assumptions, strategies, summary):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO simulation_runs (assumptions_json, strategies_json, summary_json) "
            "VALUES (%s, %s, %s)",
            (json.dumps(assumptions), json.dumps(strategies),
             summary.to_json(orient="records")),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _load(value):
    return json.loads(value) if isinstance(value, (str, bytes)) else value


def load_recent_runs(limit=20):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, created_at, assumptions_json, summary_json "
            "FROM simulation_runs ORDER BY created_at DESC LIMIT %s",
            (int(limit),),
        )
        out = []
        for row in cur.fetchall():
            a = _load(row["assumptions_json"])
            s = _load(row["summary_json"])
            best = max(s, key=lambda r: r["survival_probability"]) if s else {}
            out.append({
                "Run ID": row["id"],
                "Created At": row["created_at"],
                "Months": a.get("horizon"),
                "Simulations": a.get("n_simulations"),
                "Safest strategy": best.get("strategy", "-"),
                "Its survival": f"{best.get('survival_probability', 0):.1%}",
            })
        return pd.DataFrame(out)
    finally:
        conn.close()