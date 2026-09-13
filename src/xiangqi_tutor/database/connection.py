from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 1


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        with closing(self.connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS engine_cache (
                    cache_key TEXT PRIMARY KEY,
                    fen TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tutor_cache (
                    cache_key TEXT PRIMARY KEY,
                    fen TEXT NOT NULL,
                    model TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY,
                    event TEXT,
                    played_date TEXT,
                    red_player TEXT,
                    black_player TEXT,
                    result TEXT,
                    opening TEXT,
                    source TEXT,
                    source_license TEXT,
                    moves_json TEXT NOT NULL DEFAULT '[]',
                    fen_sequence_json TEXT NOT NULL DEFAULT '[]',
                    annotations_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def get_engine_cache(self, cache_key: str) -> dict[str, object] | None:
        with closing(self.connect()) as connection, connection:
            row = connection.execute("SELECT result_json FROM engine_cache WHERE cache_key = ?", (cache_key,)).fetchone()
        return json.loads(row["result_json"]) if row else None

    def put_engine_cache(self, cache_key: str, fen: str, settings: dict[str, object], result: dict[str, object]) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO engine_cache(cache_key, fen, settings_json, result_json) VALUES(?, ?, ?, ?)",
                (cache_key, fen, json.dumps(settings, ensure_ascii=False), json.dumps(result, ensure_ascii=False)),
            )

    def get_tutor_cache(self, cache_key: str) -> dict[str, object] | None:
        with closing(self.connect()) as connection, connection:
            row = connection.execute("SELECT response_json FROM tutor_cache WHERE cache_key = ?", (cache_key,)).fetchone()
        return json.loads(row["response_json"]) if row else None

    def put_tutor_cache(self, cache_key: str, fen: str, model: str, response: dict[str, object]) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO tutor_cache(cache_key, fen, model, response_json) VALUES(?, ?, ?, ?)",
                (cache_key, fen, model, json.dumps(response, ensure_ascii=False)),
            )
