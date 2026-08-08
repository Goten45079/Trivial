from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_RATES = {"gpt-4.1": 0.0075, "gpt-4.1-mini": 0.0016, "gpt-4.1-nano": 0.00045}
DEFAULT_BUDGET = {"monthly": 1200.0, "warning": 75.0, "errorRate": 3.0, "latency": 900}
SEED_CALLS = [
    {"id": "req_7fa1", "timestamp": "2026-08-08T09:05:00Z", "model": "gpt-4.1", "env": "Production", "prompt": 1280, "completion": 640, "latency": 920, "status": "success", "endpoint": "/chat/respond", "metadata": {"team": "support"}},
    {"id": "req_81bd", "timestamp": "2026-08-08T09:20:00Z", "model": "gpt-4.1-mini", "env": "Production", "prompt": 820, "completion": 280, "latency": 510, "status": "success", "endpoint": "/support/summarize", "metadata": {"team": "support"}},
    {"id": "req_92ac", "timestamp": "2026-08-08T10:00:00Z", "model": "gpt-4.1-mini", "env": "Staging", "prompt": 460, "completion": 190, "latency": 440, "status": "success", "endpoint": "/qa/classify", "metadata": {"team": "qa"}},
    {"id": "req_13cc", "timestamp": "2026-08-08T10:35:00Z", "model": "gpt-4.1", "env": "Production", "prompt": 2400, "completion": 970, "latency": 1380, "status": "error", "endpoint": "/chat/respond", "metadata": {"team": "support"}},
    {"id": "req_56ed", "timestamp": "2026-08-08T11:15:00Z", "model": "gpt-4.1-nano", "env": "Development", "prompt": 360, "completion": 90, "latency": 220, "status": "success", "endpoint": "/dev/extract", "metadata": {"team": "platform"}},
]


class TelemetryStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS calls (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    env TEXT NOT NULL,
                    prompt INTEGER NOT NULL,
                    completion INTEGER NOT NULL,
                    latency INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    monthly REAL NOT NULL,
                    warning REAL NOT NULL,
                    error_rate REAL NOT NULL,
                    latency INTEGER NOT NULL
                );
                """
            )
            count = connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
            if count == 0:
                self.record_many(SEED_CALLS, connection)
            connection.execute(
                "INSERT OR IGNORE INTO budgets (id, monthly, warning, error_rate, latency) VALUES (1, ?, ?, ?, ?)",
                (DEFAULT_BUDGET["monthly"], DEFAULT_BUDGET["warning"], DEFAULT_BUDGET["errorRate"], DEFAULT_BUDGET["latency"]),
            )

    def record_many(self, calls: list[dict], connection: sqlite3.Connection | None = None) -> None:
        def write(conn: sqlite3.Connection) -> None:
            conn.executemany(
                """
                INSERT OR REPLACE INTO calls
                (id, timestamp, model, env, prompt, completion, latency, status, endpoint, metadata)
                VALUES (:id, :timestamp, :model, :env, :prompt, :completion, :latency, :status, :endpoint, :metadata)
                """,
                [{**call, "metadata": json.dumps(call.get("metadata", {}))} for call in calls],
            )
        if connection is None:
            with self.connect() as conn:
                write(conn)
        else:
            write(connection)

    def record_call(self, call: dict) -> dict:
        self.record_many([call])
        return call

    def list_calls(self, model: str = "All", env: str = "All", limit: int = 500) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if model != "All":
            clauses.append("model = ?")
            params.append(model)
        if env != "All":
            clauses.append("env = ?")
            params.append(env)
        query = "SELECT * FROM calls"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_call(row) for row in rows]

    def list_models(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT DISTINCT model FROM calls ORDER BY model").fetchall()
        return [row[0] for row in rows]

    def list_environments(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT DISTINCT env FROM calls ORDER BY env").fetchall()
        return [row[0] for row in rows]

    def get_budget(self) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT monthly, warning, error_rate, latency FROM budgets WHERE id = 1").fetchone()
        return {"monthly": row["monthly"], "warning": row["warning"], "errorRate": row["error_rate"], "latency": row["latency"]}

    def update_budget(self, config: dict) -> dict:
        with self.connect() as connection:
            connection.execute(
                "UPDATE budgets SET monthly = ?, warning = ?, error_rate = ?, latency = ? WHERE id = 1",
                (config["monthly"], config["warning"], config["errorRate"], config["latency"]),
            )
        return self.get_budget()

    def _row_to_call(self, row: sqlite3.Row) -> dict:
        payload = dict(row)
        payload["metadata"] = json.loads(payload.get("metadata") or "{}")
        payload["time"] = payload["timestamp"][11:16]
        payload["tokens"] = payload["prompt"] + payload["completion"]
        payload["cost"] = (payload["tokens"] / 1000) * DEFAULT_RATES.get(payload["model"], DEFAULT_RATES["gpt-4.1-mini"])
        return payload
