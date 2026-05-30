"""SQLite persistence layer for articles and summaries."""

import logging
import sqlite3
from datetime import datetime
from typing import List, Set

from ingestion.rss_fetcher import Article

logger = logging.getLogger(__name__)

DB_PATH = "economy_digest.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    url         TEXT UNIQUE NOT NULL,
    source      TEXT,
    published_at TEXT,
    raw_summary  TEXT,
    is_relevant  INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    article_url  TEXT NOT NULL,
    summary      TEXT NOT NULL,
    digest_date  TEXT NOT NULL,
    created_at   TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (article_url) REFERENCES articles(url)
);
"""


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Create database and tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    logger.info(f"Database ready at {db_path}")
    return conn


def get_known_urls(conn: sqlite3.Connection) -> Set[str]:
    """Return all article URLs already stored (for deduplication)."""
    cursor = conn.execute("SELECT url FROM articles")
    return {row[0] for row in cursor.fetchall()}


def save_articles(conn: sqlite3.Connection, articles: List[Article]) -> None:
    """Insert articles into the database, ignoring duplicates."""
    rows = [
        (
            article.title,
            article.url,
            article.source,
            article.published_at.isoformat(),
            article.summary,
            1 if article.is_relevant else 0,
        )
        for article in articles
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO articles
            (title, url, source, published_at, raw_summary, is_relevant)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    logger.info(f"Saved {len(rows)} articles to database")


def save_summary(conn: sqlite3.Connection, article_url: str, summary: str, digest_date: str) -> None:
    """Store a Claude-generated summary for an article."""
    conn.execute(
        "INSERT INTO summaries (article_url, summary, digest_date) VALUES (?, ?, ?)",
        (article_url, summary, digest_date),
    )
    conn.commit()
