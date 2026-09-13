from __future__ import annotations

import sqlite3
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
        with self.connect() as connection:
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

