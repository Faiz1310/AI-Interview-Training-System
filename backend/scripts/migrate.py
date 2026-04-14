"""Idempotent SQLite migration helper.

Run from backend/:

    python migrate.py
"""

import os
import sqlite3
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()


def _existing_columns(cur: sqlite3.Cursor, table_name: str) -> set:
    cur.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    """Check if table exists in database."""
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None


def _ensure_columns(cur: sqlite3.Cursor, table_name: str, columns: List[Tuple[str, str]]) -> None:
    existing = _existing_columns(cur, table_name)
    for col_name, col_sql in columns:
        if col_name in existing:
            print(f"  · SKIP {table_name}.{col_name} (exists)")
            continue
        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_sql}"
        cur.execute(sql)
        print(f"  ✓ {table_name}.{col_name}")


def main() -> None:
    db_url = os.getenv("DATABASE_URL", "sqlite:///./interview_prep.db")
    if not db_url.startswith("sqlite"):
        raise RuntimeError("This migration helper is SQLite-only.")

    db_path = db_url.replace("sqlite:///./", "./").replace("sqlite:///", "")
    print(f"Migrating: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    migrations: Dict[str, List[Tuple[str, str]]] = {
        "interview_sessions": [
            ("status", "status TEXT NOT NULL DEFAULT 'active'"),
            ("ended_at", "ended_at DATETIME"),
            ("max_questions", "max_questions INTEGER NOT NULL DEFAULT 10"),
            ("current_difficulty", "current_difficulty INTEGER NOT NULL DEFAULT 2"),
            ("new_questions_count", "new_questions_count INTEGER NOT NULL DEFAULT 0"),
            ("reused_questions_count", "reused_questions_count INTEGER NOT NULL DEFAULT 0"),
            ("last_question_was_reused", "last_question_was_reused INTEGER NOT NULL DEFAULT 0"),
            ("resume_risk_flag", "resume_risk_flag INTEGER NOT NULL DEFAULT 0"),
            ("last_difficulty_change_turn", "last_difficulty_change_turn INTEGER NOT NULL DEFAULT 0"),
        ],
        "resumes": [
            ("analysis_score", "analysis_score REAL"),
            ("analysis_model_used", "analysis_model_used TEXT"),
            ("strengths", "strengths TEXT"),
            ("weaknesses", "weaknesses TEXT"),
            ("suggestions", "suggestions TEXT"),
            ("improvement_tags", "improvement_tags TEXT"),
            ("analysis_summary", "analysis_summary TEXT"),
        ],
        "interview_answers": [
            ("resume_id", "resume_id INTEGER"),
            ("normalized_question", "normalized_question TEXT"),
            ("difficulty_level", "difficulty_level INTEGER"),
            ("topic", "topic TEXT"),
            ("is_reused", "is_reused INTEGER NOT NULL DEFAULT 0"),
            ("selection_reason", "selection_reason TEXT"),
            ("selection_context", "selection_context TEXT"),
            ("previous_score", "previous_score REAL"),
            ("transcription", "transcription TEXT"),  # NEW: Speech-to-text transcription
        ],
    }

    for table, cols in migrations.items():
        _ensure_columns(cur, table, cols)

    # Create behavior_issues table if it doesn't exist (NEW TABLE for Phase 1)
    if not _table_exists(cur, "behavior_issues"):
        cur.execute("""
        CREATE TABLE behavior_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_index INTEGER NOT NULL,
            issue VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL DEFAULT 'medium',
            description TEXT,
            continuous_violation_count INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
        )
        """)
        cur.execute("CREATE INDEX idx_behavior_session ON behavior_issues(session_id)")
        cur.execute("CREATE INDEX idx_behavior_issue ON behavior_issues(issue)")
        print("✓ behavior_issues table created")
        print("  ✓ behavior_issues.idx_behavior_session index")
        print("  ✓ behavior_issues.idx_behavior_issue index")
    else:
        print("  · SKIP behavior_issues table (exists)")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
