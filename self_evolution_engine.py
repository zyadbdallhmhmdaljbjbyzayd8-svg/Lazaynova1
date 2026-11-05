#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAZAYNOVA AI - Self Evolution Engine (Interactive Edition)
==========================================================
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get("LZ_KNOWLEDGE_DB", "knowledge_core/memory_evolution.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    topic_norm TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    lang TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','verified','conflict','rejected')),
    confidence REAL NOT NULL DEFAULT 0.0,
    support INTEGER NOT NULL DEFAULT 1,
    hits INTEGER NOT NULL DEFAULT 0,
    feedback INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(topic_norm, content_hash)
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    session TEXT,
    query TEXT NOT NULL,
    lang TEXT NOT NULL,
    intent TEXT NOT NULL
);
"""

class Database:
    def __init__(self, path: str = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur

    def query(self, sql: str, params: tuple = ()) -> list:
        return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        self._conn.close()

class SelfEvolutionEngine:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db = Database(db_path)

    def teach(self, topic: str, content: str) -> dict:
        topic_norm = topic.strip().lower()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        import time
        now = time.time()
        try:
            cur = self.db.execute(
                "INSERT INTO knowledge(topic, topic_norm, content, content_hash, lang, source, status, confidence, support, hits, feedback, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'ar', 'owner', 'verified', 0.9, 1, 0, 0, ?, ?)",
                (topic, topic_norm, content, content_hash, now, now)
            )
            return {"id": cur.lastrowid, "topic": topic, "status": "verified", "action": "created"}
        except sqlite3.IntegrityError:
            return {"status": "exists", "topic": topic}

    def stats(self) -> dict:
        by_status = {r["status"]: r["n"] for r in self.db.query("SELECT status, COUNT(*) AS n FROM knowledge GROUP BY status")}
        inter = self.db.query("SELECT COUNT(*) AS n FROM interactions")[0]["n"]
        return {"knowledge": by_status, "interactions": inter}

    def close(self):
        self.db.close()

def main() -> int:
    parser = argparse.ArgumentParser(description="LAZAYNOVA self-evolution engine")
    parser.add_argument("query", nargs="*", help="keyword or prompt to expand")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--teach", nargs=2, metavar=("TOPIC", "CONTENT"), help="store verified knowledge")
    parser.add_argument("-i", "--interactive", action="store_true", help="interactive mode")
    args = parser.parse_args()

    engine = SelfEvolutionEngine(args.db)
    try:
        if args.stats:
            print(json.dumps(engine.stats(), ensure_ascii=False, indent=2))
        elif args.teach:
            print(json.dumps(engine.teach(args.teach[0], args.teach[1]), ensure_ascii=False))
        elif args.interactive:
            print("=== LAZAYNOVA Self-Evolution Interactive Mode ===")
            while True:
                try:
                    line = input("lazaynova_evo> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting.")
                    break
                if not line or line in {"exit", "quit", "خروج"}:
                    break
                print(f"Processed: {line} (Knowledge Core Active)")
        elif args.query:
            q = " ".join(args.query)
            print(f"Processing query: {q}")
    finally:
        engine.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
