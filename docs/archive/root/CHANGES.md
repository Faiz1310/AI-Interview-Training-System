# Backend Patch Notes — Production Hardening

## Files Modified

| File | Change Summary |
|------|---------------|
| `main.py` | SBERT warm-load at startup; proper logging setup; CORS confirmed before routers |
| `services/ai_service.py` | Retry logic (1 retry), timeouts (20s), `*_safe()` variants with structured fallback JSON |
| `ai_modules/correctness.py` | All sub-scorers wrapped in try/except; SBERT failure returns 60.0 fallback; warm-load compatible |
| `routes/session_routes.py` | Answer validation (≤2000 chars, ≥3 words) via Pydantic; duplicate question guard; session ownership check; status == "active" guard |
| `routes/resume_routes.py` | `analyze_resume` now accepts `{resume_id}` body; uses `gemini_generate_safe`; proper logging |
| `routes/behavior_routes.py` | Pydantic `field_validator` clamps all metrics; status guard added; window_metrics returned |
| `requirements.txt` | Added `python-docx`; confirmed all required packages present |
| `.env.example` | Expanded with PostgreSQL example and generation instructions |

## What Was Already Correct (No Changes Needed)

- **Secrets in .env** — `jwt_handler.py` and `database.py` already use `os.getenv()`
- **CORS middleware** — already configured correctly in `main.py` before routers
- **Scoring weights 50/25/25** — `hierarchical.py` already correct
- **`/end_session`** — already implemented with `status`, `ended_at`, and coach feedback
- **`GET /resumes`** — already implemented
- **`POST /analyze_resume`** — already implemented (signature changed to accept body)
- **Session ownership checks** — already present in most routes
- **Fallback questions** — `rag.py` already has `FALLBACK_QUESTIONS` and proper JSON parsing
- **Question list format** — already returns `[{question, type}]`

## Database Migration

The schema is already up-to-date in the models. If you have an **existing database** from a previous version, run:

```python
# Run once from the backend/ directory
from database import init_db
init_db()
```

`SQLAlchemy`'s `create_all` is safe to re-run — it only creates missing tables/columns it can detect as new tables, but does NOT add new columns to existing tables automatically.

### If upgrading an existing SQLite database, run this migration script:

```python
# backend/migrate.py — run once: python migrate.py
import sqlite3, os
db_path = os.getenv("DATABASE_URL", "sqlite:///./interview_prep.db").replace("sqlite:///", "")

conn = sqlite3.connect(db_path)
cur  = conn.cursor()

# Add columns that may be missing from older schema
migrations = [
    "ALTER TABLE interview_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
    "ALTER TABLE interview_sessions ADD COLUMN ended_at DATETIME",
    "ALTER TABLE resumes ADD COLUMN analysis_score REAL",
    "ALTER TABLE resumes ADD COLUMN strengths TEXT",
    "ALTER TABLE resumes ADD COLUMN weaknesses TEXT",
    "ALTER TABLE resumes ADD COLUMN suggestions TEXT",
    "ALTER TABLE resumes ADD COLUMN improvement_tags TEXT",
    "ALTER TABLE resumes ADD COLUMN analysis_summary TEXT",
]

for sql in migrations:
    try:
        cur.execute(sql)
        print(f"OK: {sql[:60]}")
    except sqlite3.OperationalError as e:
        print(f"SKIP (already exists): {e}")

conn.commit()
conn.close()
print("Migration complete.")
```

## Key Behaviour Changes

### Answer Validation (session_routes.py)
- Answers > 2000 characters → `400 Bad Request`
- Empty answers → `400 Bad Request`  
- Answers < 3 words → `400 Bad Request`
- Duplicate questions in same session → `400 Bad Request`

### AI Fallbacks (ai_service.py)
- All Groq/Gemini calls retry once after a 1-second pause
- On 2nd failure, `*_safe()` functions return structured fallback JSON
- Server **never crashes** from AI unavailability

### Behavioral Metrics (behavior_routes.py)
- `eye_contact_score`, `head_stability_score`, `facial_stress_index` are **auto-clamped to [0,1]**
- `blink_rate` is **auto-clamped to ≥ 0** (unit: blinks per minute)
- Session must be `active` to accept metrics

### analyze_resume (resume_routes.py)
- Now accepts a JSON body `{ "resume_id": int }` (was a query param)
- Returns cached result if already analyzed
