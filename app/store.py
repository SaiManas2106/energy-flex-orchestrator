"""Small SQLite repository used to demonstrate telemetry and plan persistence."""

import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str = "energy_flex.db") -> None:
        self.path = path
        self._initialise()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS telemetry (
                asset_id TEXT NOT NULL, timestamp TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY (asset_id, timestamp))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS optimisation_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT NOT NULL,
                result TEXT NOT NULL)""")

    def upsert_telemetry(self, asset_id: str, points: list[dict]) -> None:
        with self._connect() as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO telemetry(asset_id, timestamp, payload) VALUES (?, ?, ?)",
                [(asset_id, point["timestamp"], json.dumps(point)) for point in points],
            )

    def get_telemetry(self, asset_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM telemetry WHERE asset_id = ? ORDER BY timestamp", (asset_id,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_plan(self, asset_id: str, result: dict) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO optimisation_plans(asset_id, result) VALUES (?, ?)", (asset_id, json.dumps(result))
            )
        return int(cursor.lastrowid)

    def get_plan(self, plan_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT asset_id, result FROM optimisation_plans WHERE plan_id = ?", (plan_id,)).fetchone()
        return None if row is None else {"plan_id": plan_id, "asset_id": row[0], **json.loads(row[1])}
