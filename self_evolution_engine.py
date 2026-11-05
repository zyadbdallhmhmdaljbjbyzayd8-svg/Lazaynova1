#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAZAYNOVA AI - Self Evolution Engine
====================================
Keyword-to-conversation expansion + continuous learning loop on top of a local
SQLite knowledge core (default: knowledge_core/memory_evolution.db).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import queue
import re
import sqlite3
import sys
import threading
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Protocol, Sequence, Tuple

LOG = logging.getLogger("lazaynova.evolution")

DEFAULT_DB_PATH = os.environ.get("LZ_KNOWLEDGE_DB", "knowledge_core/memory_evolution.db")
MIN_SCORE = 0.40
MAX_FACT_CHARS = 1500
MIN_FACT_CHARS = 8
MAX_FACTS_PER_MESSAGE = 5

_AR_MARKS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]")
_AR_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    "ک": "ك", "ی": "ي",
})
_ARABIC_LETTER = re.compile(r"[\u0621-\u064A\u066E-\u06D3]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")
_WORD = re.compile(r"\w+", re.UNICODE)

def strip_arabic_marks(text: str) -> str:
    return _AR_MARKS.sub("", (text or "").replace("\u0640", ""))

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = strip_arabic_marks(text).translate(_AR_FOLD).casefold()
    return re.sub(r"\s+", " ", text).strip()

def detect_language(text: str) -> str:
    ar = len(_ARABIC_LETTER.findall(text or ""))
    en = len(_LATIN_LETTER.findall(text or ""))
    return "ar" if ar >= en and ar > 0 else "en"

_STOP_RAW = """
في من على الى إلى عن ما ماذا هل هو هي هم هذا هذه ذلك تلك التي الذي الذين مع او أو ثم كان كانت لا
كيف لماذا متى اين أين كم اي أي ان أن إن قد لقد بعد قبل عند حتى بين لكن اذا إذا يا انا أنا نحن انت أنت
اشرح شرح عرف تعريف اخبرني أخبرني قل لي اعطني أعطني وضح بالتفصيل
a an the is are was were of to in on for and or with what how why when where who which do does did can
i you it this that be as at by from my me about please explain define tell give
"""
STOPWORDS = {normalize_text(w) for w in _STOP_RAW.split()}
_AR_PREFIXES = sorted({normalize_text(p) for p in ("وال", "بال", "كال", "فال", "لل", "ال", "و", "ف", "ب", "ك", "ل")}, key=len, reverse=True)
_AR_SUFFIXES = sorted({normalize_text(s) for s in ("ات", "ان", "ون", "ين", "ها", "هم", "هن", "ية", "ه", "ي", "ك")}, key=len, reverse=True)

def stem_token(token: str) -> str:
    if _ARABIC_LETTER.search(token):
        for prefix in _AR_PREFIXES:
            if token.startswith(prefix) and len(token) - len(prefix) >= 3:
                token = token[len(prefix):]
                break
        for suffix in _AR_SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                token = token[: -len(suffix)]
                break
        return token
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token

def content_tokens(text: str) -> List[str]:
    out: List[str] = []
    for tok in _WORD.findall(normalize_text(text)):
        if tok in STOPWORDS or len(tok) < 2:
            continue
        tok = stem_token(tok)
        if len(tok) >= 2:
            out.append(tok)
    return out

def topic_key(text: str) -> str:
    return " ".join(content_tokens(text))

def query_key(text: str) -> str:
    return " ".join(sorted(set(content_tokens(text))))

_SENSITIVE = re.compile(r"(?:sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:password|passwd|token|secret|api[_-]?key)\s*[:=]|(?:كلمة\s*(?:ال)?سر|رمز\s*(?:ال)?دخول)\s*[:=])", re.IGNORECASE)

def looks_sensitive(text: str) -> bool:
    return bool(_SENSITIVE.search(text or ""))

_FENCE = re.compile(r"```[^\n`]*\n.*?```", re.DOTALL)
_QUESTION_WORDS = {normalize_text(w) for w in ("ما", "ماذا", "هل", "كيف", "لماذا", "متى", "اين", "أين", "من", "كم", "اي", "أي", "what", "how", "why", "when", "where", "who", "which", "is", "are", "does", "do", "can", "could", "should")}

def is_question(text: str) -> bool:
    stripped = (text or "").strip()
    if stripped.endswith(("?", "؟")):
        return True
    first = _WORD.findall(normalize_text(stripped))[:1]
    return bool(first) and first[0] in _QUESTION_WORDS

_TEACH_AR = re.compile(r"^\s*(?:تذكر|اعلم|احفظ|لاحظ|سجل)\s*(?:انه|أنه|ان|أن|إن)?\s*[:：]?\s*(?P<body>.+)$", re.S)
_TEACH_EN = re.compile(r"^\s*(?:remember|note|keep in mind)\s*(?:that)?\s*[:：]?\s*(?P<body>.+)$", re.I | re.S)
_COLON = re.compile(r"^\s*(?P<topic>[^:：\n]{2,60})\s*[:：]\s*(?P<content>.{6,})$", re.S)
_DEF_AR = re.compile(r"^\s*(?P<topic>[^\n\.،,؛:]{2,60}?)\s+(?:هو|هي|هم|هما|يعني|تعني|يقصد به|يعرف بانه|يعرف بأنه|تعرف بانها|تعرف بأنها)\s+(?P<content>.{6,})$", re.S)
_DEF_EN = re.compile(r"^\s*(?P<topic>[^\n\.,;:]{2,60}?)\s+(?:is|are|means|refers to|stands for)\s+(?P<content>.{6,})$", re.I | re.S)
_SENTENCE_SPLIT = re.compile(r"(?<=[\.\!\n؟?])\s+")
_NEGATIONS = {normalize_text(w) for w in ("لا", "ليس", "ليست", "لم", "لن", "غير", "not", "no", "never", "isn't", "aren't")}

def _split_topic_content(body: str) -> Optional[Tuple[str, str]]:
    body = strip_arabic_marks(body).strip()
    for pattern in (_COLON, _DEF_AR, _DEF_EN):
        m = pattern.match(body)
        if m:
            return m.group("topic").strip(" \t\"'«»"), m.group("content").strip()
    return None

def extract_facts(text: str) -> List[Tuple[str, str, str]]:
    clean = _FENCE.sub(" ", text or "")
    facts: List[Tuple[str, str, str]] = []
    for sentence in _SENTENCE_SPLIT.split(clean):
        sentence = sentence.strip()
        if not sentence or is_question(sentence):
            continue
        kind, body = "statement", sentence
        for pattern in (_TEACH_AR, _TEACH_EN):
            m = pattern.match(sentence)
            if m:
                kind, body = "teach", m.group("body")
                break
        if kind == "teach":
            pair = _split_topic_content(body)
        else:
            pair = None
            stripped = strip_arabic_marks(body)
            for pattern in (_DEF_AR, _DEF_EN):
                m = pattern.match(stripped)
                if m:
                    pair = (m.group("topic").strip(" \t\"'«»"), m.group("content").strip())
                    break
        if pair is None:
            continue
        facts.append((pair[0], pair[1].rstrip(" \t"), kind))
        if len(facts) >= MAX_FACTS_PER_MESSAGE:
            break
    return facts

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
CREATE TABLE IF NOT EXISTS knowledge_tokens (
    token TEXT NOT NULL,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    PRIMARY KEY (token, knowledge_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_tokens_token ON knowledge_tokens(token);
CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic_norm);
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
CREATE TABLE IF NOT EXISTS topic_stats (
    token TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0,
    last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS query_links (
    query_key TEXT NOT NULL,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    score INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (query_key, knowledge_id)
);
"""

class Database:
    def __init__(self, path: str | os.PathLike = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._tx_depth = 0
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            self._tx_depth += 1
            try:
                yield
            except BaseException:
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    self._conn.rollback()
                raise
            else:
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    self._conn.commit()

    def execute(self, sql: str, params: Sequence = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            if self._tx_depth == 0:
                self._conn.commit()
            return cur

    def query(self, sql: str, params: Sequence = ()) -> List[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, tuple(params)).fetchall()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.commit()
            finally:
                self._conn.close()

@dataclass
class KnowledgeItem:
    id: int
    topic: str
    content: str
    lang: str
    source: str
    status: str
    confidence: float
    support: int
    hits: int
    feedback: int
    score: float = 0.0

    @classmethod
    def from_row(cls, row: sqlite3.Row, score: float = 0.0) -> "KnowledgeItem":
        return cls(row["id"], row["topic"], row["content"], row["lang"], row["source"], row["status"], row["confidence"], row["support"], row["hits"], row["feedback"], score)

@dataclass
class Expansion:
    query: str
    lang: str
    intent: str
    title: str
    found: bool
    definition: Optional[KnowledgeItem] = None
    details: List[KnowledgeItem] = field(default_factory=list)
    unconfirmed: List[KnowledgeItem] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    model_draft: Optional[str] = None
    interaction_id: int = 0

    @property
    def matched_ids(self) -> List[int]:
        ids = [i.id for i in ([self.definition] if self.definition else []) + self.details + self.unconfirmed]
        return list(dict.fromkeys(ids))

    def render(self) -> str:
        ar = self.lang == "ar"
        out: List[str] = []
        if self.definition is not None:
            out.append(f"## {self.title}")
            tag = "" if self.definition.status == "verified" else (" (غير مؤكد)" if ar else " (unconfirmed)")
            out.append(("**التعريف:** " if ar else "**Definition:** ") + self.definition.content + tag)
            if self.details:
                out.append("**تفاصيل إضافية:**" if ar else "**More details:**")
                out += [f"- {d.content}" if d.topic == self.definition.topic else f"- {d.topic}: {d.content}" for d in self.details]
            if self.unconfirmed:
                out.append("**معلومات غير مؤكدة بعد:**" if ar else "**Not yet confirmed:**")
                out += [f"- {u.topic}: {u.content}" for u in self.unconfirmed]
            if self.related:
                out.append(("**مواضيع ذات صلة:** " if ar else "**Related topics:** ") + ("، " if ar else ", ").join(self.related))
        else:
            out.append(f"لا توجد معلومات موثقة عن «{self.title}»." if ar else f"No verified information about \"{self.title}\".")
        return "\n\n".join(p for p in out if p)

class SelfEvolutionEngine:
    def __init__(self, db_path: str | os.PathLike = DEFAULT_DB_PATH) -> None:
        self.db = Database(db_path)

    def close(self) -> None:
        self.db.close()

    def stats(self) -> Dict[str, object]:
        by_status = {r["status"]: r["n"] for r in self.db.query("SELECT status, COUNT(*) AS n FROM knowledge GROUP BY status")}
        inter = self.db.query("SELECT COUNT(*) AS n, COALESCE(SUM(feedback),0) AS fb FROM interactions")[0]
        return {"knowledge": by_status, "interactions": inter["n"], "feedback_sum": inter["fb"]}

def main() -> int:
    parser = argparse.ArgumentParser(description="LAZAYNOVA self-evolution engine")
    parser.add_argument("query", nargs="*", help="keyword or prompt to expand")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()
    engine = SelfEvolutionEngine(args.db)
    try:
        if args.stats:
            print(json.dumps(engine.stats(), ensure_ascii=False, indent=2))
        elif args.query:
            print(f"Processing query: {' '.join(args.query)}")
    finally:
        engine.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
