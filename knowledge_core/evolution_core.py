#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LAZAYNOVA Knowledge Evolution Core — local, auditable memory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

DEFAULT_DB = "knowledge_core/memory_evolution.db"

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
    intent TEXT NOT NULL,
    matched TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}',
    feedback INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS knowledge_tokens (
    token TEXT NOT NULL,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    PRIMARY KEY(token, knowledge_id)
);

CREATE TABLE IF NOT EXISTS topic_stats (
    token TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0,
    last_seen REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_topic
ON knowledge(topic_norm);

CREATE INDEX IF NOT EXISTS idx_knowledge_tokens_token
ON knowledge_tokens(token);
"""

ARABIC_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")
TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u0600-\u06FF]+")

STOP_WORDS = {
    "في", "من", "على", "الى", "إلى", "عن", "مع", "هذا", "هذه",
    "ذلك", "تلك", "هو", "هي", "ما", "ماذا", "كيف", "هل", "ثم",
    "كان", "كانت", "يكون", "تم", "كل", "او", "أو", "و", "ب", "ل",
    "the", "a", "an", "and", "or", "is", "are", "to", "of", "in",
    "on", "for", "with", "what", "how", "this", "that"
}


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = ARABIC_DIACRITICS.sub("", text)
    text = text.replace("ـ", "")
    return text.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"
    }))


def tokenize(text: str) -> list[str]:
    normalized = normalize(text)
    return list(dict.fromkeys(
        token for token in TOKEN_PATTERN.findall(normalized)
        if len(token) > 1 and token not in STOP_WORDS
    ))


def detect_language(text: str) -> str:
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"


class KnowledgeEvolution:
    def __init__(self, db_path: str = DEFAULT_DB, initialize: bool = False):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=15)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")

        if initialize:
            self.initialize()

    def initialize(self) -> None:
        """Create missing tables only; never drop or replace existing data."""
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def teach(
        self,
        topic: str,
        content: str,
        source: str = "termux_owner"
    ) -> dict:
        topic = topic.strip()
        content = content.strip()

        if not topic or not content:
            raise ValueError("Topic and content must not be empty.")

        topic_norm = normalize(topic)
        content_hash = hashlib.sha256(
            normalize(content).encode("utf-8")
        ).hexdigest()
        now = time.time()
        tokens = tokenize(topic + " " + content)

        try:
            with self.conn:
                cur = self.conn.execute(
                    """
                    INSERT INTO knowledge (
                        topic, topic_norm, content, content_hash,
                        lang, source, status, confidence, support,
                        hits, feedback, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 0.5, 1, 0, 0, ?, ?)
                    """,
                    (
                        topic, topic_norm, content, content_hash,
                        detect_language(content), source, now, now
                    )
                )
                knowledge_id = cur.lastrowid

                for token in tokens:
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO knowledge_tokens(token, knowledge_id)
                        VALUES (?, ?)
                        """,
                        (token, knowledge_id)
                    )
                    self.conn.execute(
                        """
                        INSERT INTO topic_stats(token, count, last_seen)
                        VALUES (?, 1, ?)
                        ON CONFLICT(token) DO UPDATE SET
                            count = count + 1,
                            last_seen = excluded.last_seen
                        """,
                        (token, now)
                    )

            return {
                "id": knowledge_id,
                "topic": topic,
                "status": "pending",
                "tokens_indexed": len(tokens)
            }

        except sqlite3.IntegrityError:
            row = self.conn.execute(
                """
                SELECT id FROM knowledge
                WHERE topic_norm=? AND content_hash=?
                """,
                (topic_norm, content_hash)
            ).fetchone()
            return {
                "id": row["id"] if row else None,
                "topic": topic,
                "status": "exists"
            }

    def verify(self, knowledge_id: int, status: str = "verified") -> bool:
        """Owner-controlled review; no automatic fact verification."""
        if status not in {"verified", "pending", "conflict", "rejected"}:
            raise ValueError("Unsupported knowledge status.")

        with self.conn:
            cur = self.conn.execute(
                """
                UPDATE knowledge
                SET status=?, confidence=?, updated_at=?
                WHERE id=?
                """,
                (
                    status,
                    0.9 if status == "verified" else 0.0,
                    time.time(),
                    knowledge_id
                )
            )
        return cur.rowcount == 1

    def reindex(self) -> int:
        """Add missing token links for existing knowledge; never delete rows."""
        rows = self.conn.execute(
            "SELECT id, topic, content FROM knowledge"
        ).fetchall()
        added = 0
        now = time.time()

        with self.conn:
            for row in rows:
                for token in tokenize(row["topic"] + " " + row["content"]):
                    cur = self.conn.execute(
                        """
                        INSERT OR IGNORE INTO knowledge_tokens(token, knowledge_id)
                        VALUES (?, ?)
                        """,
                        (token, row["id"])
                    )
                    added += cur.rowcount

                    self.conn.execute(
                        """
                        INSERT INTO topic_stats(token, count, last_seen)
                        VALUES (?, 1, ?)
                        ON CONFLICT(token) DO UPDATE SET
                            last_seen = excluded.last_seen
                        """,
                        (token, now)
                    )
        return added

    def search(
        self,
        query: str,
        limit: int = 5,
        include_pending: bool = False
    ) -> list[dict]:
        tokens = tokenize(query)
        if not tokens:
            return []

        placeholders = ",".join("?" for _ in tokens)
        status_filter = (
            "k.status IN ('verified','pending')"
            if include_pending else "k.status='verified'"
        )

        rows = self.conn.execute(
            f"""
            SELECT k.id, k.topic, k.content, k.status,
                   k.confidence, COUNT(DISTINCT kt.token) AS matched_tokens
            FROM knowledge k
            JOIN knowledge_tokens kt ON kt.knowledge_id = k.id
            WHERE kt.token IN ({placeholders})
              AND {status_filter}
            GROUP BY k.id
            ORDER BY matched_tokens DESC, k.confidence DESC, k.updated_at DESC
            LIMIT ?
            """,
            (*tokens, max(1, min(limit, 20)))
        ).fetchall()

        results = [dict(row) for row in rows]

        if results:
            with self.conn:
                self.conn.executemany(
                    "UPDATE knowledge SET hits=hits+1 WHERE id=?",
                    [(row["id"],) for row in results]
                )
        return results

    def record_interaction(
        self,
        query: str,
        intent: str = "chat",
        matched_ids: list[int] | None = None,
        session: str | None = None,
        feedback: int = 0
    ) -> int:
        if feedback not in (-1, 0, 1):
            raise ValueError("Feedback must be -1, 0, or 1.")

        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO interactions(
                    ts, session, query, lang, intent, matched, meta, feedback
                ) VALUES (?, ?, ?, ?, ?, ?, '{}', ?)
                """,
                (
                    time.time(), session, query, detect_language(query),
                    intent, json.dumps(matched_ids or []), feedback
                )
            )
        return int(cur.lastrowid)

    def stats(self) -> dict:
        statuses = {
            row["status"]: row["n"]
            for row in self.conn.execute(
                "SELECT status, COUNT(*) AS n FROM knowledge GROUP BY status"
            )
        }
        interactions = self.conn.execute(
            "SELECT COUNT(*) FROM interactions"
        ).fetchone()[0]
        tokens = self.conn.execute(
            "SELECT COUNT(*) FROM knowledge_tokens"
        ).fetchone()[0]

        return {
            "knowledge_by_status": statuses,
            "interaction_count": interactions,
            "indexed_token_links": tokens
        }

    def close(self) -> None:
        self.conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LAZAYNOVA local knowledge evolution core"
    )
    parser.add_argument("--db", default=DEFAULT_DB)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init")
    commands.add_parser("stats")
    commands.add_parser("reindex")

    teach_parser = commands.add_parser("teach")
    teach_parser.add_argument("topic")
    teach_parser.add_argument("content")

    search_parser = commands.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--pending", action="store_true")

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("id", type=int)
    verify_parser.add_argument(
        "--status",
        choices=["verified", "pending", "conflict", "rejected"],
        default="verified"
    )

    args = parser.parse_args()
    engine = KnowledgeEvolution(args.db, initialize=args.command == "init")

    try:
        if args.command == "init":
            print("Schema initialized without dropping existing data.")
        elif args.command == "stats":
            print(json.dumps(engine.stats(), ensure_ascii=False, indent=2))
        elif args.command == "reindex":
            print(json.dumps({"new_token_links": engine.reindex()}))
        elif args.command == "teach":
            print(json.dumps(
                engine.teach(args.topic, args.content),
                ensure_ascii=False
            ))
        elif args.command == "search":
            print(json.dumps(
                engine.search(args.query, include_pending=args.pending),
                ensure_ascii=False,
                indent=2
            ))
        elif args.command == "verify":
            print(json.dumps({
                "updated": engine.verify(args.id, args.status),
                "id": args.id,
                "status": args.status
            }))
    finally:
        engine.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
