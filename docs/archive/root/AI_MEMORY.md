# AI Interview Training System — Repository Memory

## PROJECT OVERVIEW
**Type**: Full-stack multimodal AI interview training platform  
**Architecture**: Layered N-tier (React SPA + FastAPI backend)  
**Purpose**: Train candidates via AI-driven interviews with 3-dimensional evaluation (Correctness, Clarity, Confidence)  
**Status**: Production-ready with fallback mechanisms  
**Version**: 2.0.0 (production hardened)

## CORE PHILOSOPHY
- **Three Decoupled Dimensions**: Correctness (knowledge), Clarity (communication), Confidence (behavioral) scored independently
- **Coaching-First**: Supportive feedback, not punitive evaluation
- **Multimodal Fusion**: Video (MediaPipe) + Audio (Librosa) + Text (NLP) combined for confidence
- **Graceful Degradation**: System functions even if AI APIs fail
- **Hybrid Scoring**: LLM + classical ML + rule-based for robustness

---

## DIRECTORY STRUCTURE

### Backend (`backend/`)
```
main.py               → FastAPI app + CORS + lifespan (DB init, SBERT warm-load)
database.py           → SQLAlchemy engine + SessionLocal + Base + init_db()
migrate.py            → SQLite schema upgrade script (ALTER TABLE statements)

auth/
  jwt_handler.py      → create_access_token(), verify_token() (HS256, 120min expiry)

models/
  user.py             → User (id, name, email, password_hash, is_active, created_at)
  resume.py           → Resume (id, user_id, resume_text, jd_text, job_role, filename, analysis_*, created_at)
  session.py          → InterviewSession (id, user_id, resume_id, status, scores×5, performance_label, coach_message, created_at, ended_at)
  answer.py           → InterviewAnswer (id, session_id, question, answer, scores×4, explanations×3, sub_scores×3, created_at)
  behavior_metric.py  → InterviewBehaviorMetric (id, session_id, eye_contact, head_stability, blink_rate, stress, created_at)

routes/
  auth_routes.py      → POST /register, /login, GET /me
  resume_routes.py    → POST /upload_resume, /analyze_resume, GET /resumes
  question_routes.py  → POST /generate_questions (RAG pipeline)
  session_routes.py   → POST /start_session, /submit_answer, /end_session
  behavior_routes.py  → POST /submit_behavior_metrics, /analyze_audio
  dashboard_routes.py → GET /dashboard, /session/{id}

services/
  ai_service.py       → Centralized Groq + Gemini wrappers (retry+timeout+fallback)
  text_extractor.py   → PDF/DOCX/TXT parser (PyPDF2, python-docx)

ai_modules/
  rag.py              → FAISS indexing + Groq question generation + fallback questions
  correctness.py      → 60%LLM + 25%SBERT + 15%keyword + length_factor + Gemini explanation
  clarity.py          → Rule-based (length, repetition, fillers, structure)
  behavioral_confidence.py → Multimodal fusion (60%video + 25%audio + 15%text)
  hierarchical.py     → Final = 0.50×C + 0.30×CL + 0.20×CF
  feedback_generator.py → generate_answer_feedback(), generate_session_summary()
  video_analyzer.py   → MediaPipe landmark processing (eye contact, stability, blink, stress)
  audio_analyzer.py   → Librosa (speech rate, pause, pitch, energy) + text hesitation

vector_store/
  {resume_id}.index         → FAISS L2 index (binary format)
  {resume_id}_chunks.pkl    → Pickled text chunks (300 words each)
```

### Frontend (`frontend/src/`)
```
App.jsx               → Root router (login|dashboard|upload|interview pages)
main.jsx              → ReactDOM.render() entry point

components/
  LoginRegisterPage.jsx     → JWT auth UI (toggle login/register)
  ResumeUploadPage.jsx      → Multipart form (resume_file, jd_file, jd_text, job_role)
  InterviewPage.jsx         → Live interview conductor (speech rec + camera + scoring)
  CameraFeed.jsx            → MediaPipe FaceMesh integration (468 landmarks → metrics every 2s)
  DashboardPage.jsx         → Chart.js radar + line charts (progress trends)

hooks/
  useSpeechRecognition.js   → Web Speech API wrapper (continuous=true, interimResults=true, auto-restart)
  useAudioRecorder.js       → MediaRecorder blob capture
  useAnswerSubmit.js        → Answer submission logic

services/
  authService.js            → Axios wrappers (login, register, getMe)
```

---

## TECHNOLOGY STACK

### AI Models
| Model | Provider | Purpose | Config |
|-------|----------|---------|--------|
| **LLaMA 3.3 70B** | Groq API | Question gen + correctness scoring | temp 0.1-0.7, timeout 20s, 1 retry |
| **Gemini 1.5 Flash** | Google AI | Resume analysis + explanations | temp 0.3-0.4, fallback to 1.0 Pro |
| **SBERT (all-MiniLM-L6-v2)** | Local | 384-dim embeddings + cosine sim | Warm-loaded at startup |
| **MediaPipe FaceMesh** | Client TF.js | 468 facial landmarks @ 30 FPS | CDN-loaded, GPU WebGL |

### Backend Stack
FastAPI 0.109+ • SQLAlchemy 2.0+ • SQLite/PostgreSQL • JWT (PyJWT 2.8) • bcrypt • FAISS CPU • librosa

### Frontend Stack
React 18.2 • Vite 5.0 • TailwindCSS 3.3 • Axios • Chart.js 4.5 • MediaPipe 0.4 • Web Speech API

---

## SYSTEM ARCHITECTURE

### Request Lifecycle: Answer Submission

1. **Frontend Capture**:
   - User speaks → Web Speech API (`continuous=true`, auto-restart on `onend`)
   - CameraFeed → MediaPipe landmarks → metrics every 2s → `POST /submit_behavior_metrics`
   - MediaRecorder → audio blob → `POST /analyze_audio` → audio_confidence

2. **API Call**: `POST /submit_answer`
   ```json
   {
     "session_id": 123,
     "question": "Explain SOLID principles",
     "answer": "SOLID stands for...",
     "question_type": "technical",
     "audio_confidence": 72.5
   }
   ```

3. **Backend Processing** (session_routes.py):
   - **Guards**: JWT verify, session ownership, status="active", duplicate question check, length validation (3-2000 chars)
   - **Correctness**: `evaluate_correctness()` → Groq LLM (60%) + SBERT cosine (25%) + keyword (15%) × length_factor
   - **Clarity**: `evaluate_clarity()` → penalties for short/repetitive/filler/broken structure
   - **Confidence**: `compute_multimodal_confidence()` → fuse video (60%, from rolling window) + audio (25%) + text hesitation (15%)
   - **Overall**: `compute_overall()` → 0.50×C + 0.30×CL + 0.20×CF
   - **Feedback**: `generate_answer_feedback()` → strengths, areas_to_improve, coaching_tip
   - **Persist**: InterviewAnswer record + update session averages
   
4. **Response**:
   ```json
   {
     "current_answer": {
       "correctness": 72.5,
       "clarity": 81.0,
       "confidence": 65.3,
       "overall": 72.8,
       "correctness_explanation": "Good coverage of SRP and OCP...",
       "improvement_tip": "Add specific code examples",
       "sub_scores": {"llm": 75, "cosine": 68, "keyword": 70}
     },
     "session_average": { "overall": 70.2, ... }
   }
   ```

### RAG Pipeline (Question Generation)

1. **Indexing** (on resume upload):
   - Chunk resume + JD into 300-word segments
   - SBERT encode → 384-dim vectors each
   - FAISS IndexFlatL2 → L2 distance index
   - Persist `{resume_id}.index` + `{resume_id}_chunks.pkl`

2. **Retrieval** (on question gen):
   - Query: "Generate questions based on skills, projects, gaps"
   - FAISS search → top-5 chunks (~1500 chars context)

3. **Generation** (Groq LLaMA 3.3):
   - Prompt: Inject chunks + job role + "Must reference resume specifics"
   - Output: JSON array of 10 questions × {question, type}
   - Fallback: Pre-defined generic questions if Groq fails

### Multimodal Confidence Fusion

**Video (60% weight)** — `CameraFeed.jsx` → MediaPipe:
- Eye contact (40%): Iris position relative to eye center
- Head stability (30%): Nose tip movement (10-frame window)
- Blink rate (20%): EAR < 0.21 threshold → blinks/min
- Facial stress (10%): Brow furrow + lip tension

**Audio (25% weight)** — `audio_analyzer.py` → Librosa:
- Speech rate (30%): Onset detection → syllables/min (ideal: 135 WPM)
- Pause duration (30%): RMS silence ratio
- Pitch variation (25%): F0 std dev (ideal: 0.2-0.5)
- Energy variation (15%): RMS coefficient of variation

**Text (15% weight)** — `analyze_text_hesitation()`:
- Regex patterns: um/uh/like/"you know"/ellipsis/etc
- Hesitation score: 1.0 - (matches/words)×5

**Fusion**:
```python
weights = {video: 0.60, audio: 0.25, text: 0.15}
# Normalize if some missing (e.g., no audio uploaded)
confidence = Σ(weight × score) / Σ(weights_present)
```

---

## API ENDPOINTS

### Authentication
- `POST /register` → {name, email, password} → JWT token
- `POST /login` → {email, password} → JWT token
- `GET /me` → user profile (requires Bearer token)

### Resume Management
- `POST /upload_resume` → multipart {resume_file, job_role, jd_file?, jd_text?} → resume_id
- `GET /resumes` → list user resumes
- `POST /analyze_resume` → {resume_id} → Gemini gap analysis (cached)

### Question Generation
- `POST /generate_questions` → {resume_id} → 10 questions × {question, type}

### Interview Session
- `POST /start_session` → {resume_id, total_questions?} → session_id
- `POST /submit_answer` → {session_id, question, answer, ...} → scores + feedback
- `POST /end_session` → {session_id} → performance_label + coach_message + recommendations

### Behavioral Metrics
- `POST /submit_behavior_metrics` → {session_id, eye_contact, head_stability, blink_rate, stress} → behavioral_confidence + nudge?
- `POST /analyze_audio` → multipart {audio_file, session_id} → audio_confidence

### Analytics
- `GET /dashboard?resume_id={optional}` → session_summary + progress_trend + skill_breakdown
- `GET /session/{session_id}` → detailed answer-by-answer breakdown

---

## DATABASE SCHEMA

**Relationships**:
```
User (1:N) → Resume (1:N) → InterviewSession (1:N) → InterviewAnswer
                                            (1:N) → InterviewBehaviorMetric
```

**Key Fields**:
- `users`: email (UNIQUE), password_hash (bcrypt), is_active
- `resumes`: resume_text, jd_text, job_role, analysis_* (Gemini output, JSON stored as TEXT)
- `interview_sessions`: status (active|completed), scores×5, performance_label, coach_message, ended_at
- `interview_answers`: question, answer, scores×4, explanations×3, sub_scores×3 (llm, cosine, keyword)
- `interview_behavior_metrics`: eye_contact, head_stability, blink_rate, stress (all clamped 0-1)

**Indexes**: email (unique), user_id (FK), session_id (FK)

**Cascade Deletes**: Deleting user → deletes resumes → deletes sessions → deletes answers + metrics

---

## KEY WORKFLOWS

### 1. User Registration → Interview → Dashboard
```
Register → Login (JWT) → Upload Resume → Analyze Resume (Gemini) → Generate Questions (RAG) 
→ Start Session → [Answer Loop: MediaPipe stream + Speech Rec + Submit Answer] 
→ End Session (Coach Feedback) → View Dashboard (Radar Chart + Trends)
```

### 2. Answer Evaluation Pipeline
```
Submit Answer → JWT Verify → Ownership Check → Status Guard → Duplicate Check
→ Correctness (Groq+SBERT+Keyword) || Clarity (Rules) || Confidence (Fusion)
→ Overall (50/30/20) → Feedback (Coaching) → Persist → Return Scores
```

### 3. Real-Time Behavioral Coaching
```
MediaPipe (every 33ms) → Aggregate (every 2s) → POST /submit_behavior_metrics
→ Rolling Window DB Query → Confidence Score → Nudge Generation ("Maintain eye contact")
→ Display 5s → Auto-Clear
```

---

## SCORING FORMULAS

### Correctness (ai_modules/correctness.py)
```python
llm_score = groq_chat("Evaluate 0-100") → 60% weight
cosine_score = cosine_similarity(sbert(Q), sbert(A)) × 100 → 25% weight
keyword_score = (question_keywords ∩ answer_keywords) / len(question_keywords) × 100 → 15% weight
length_factor = {0.5 if <10 words, 0.75 if <25, 1.0 if <300, 0.95 if ≥300}
final = (0.60×llm + 0.25×cosine + 0.15×keyword) × length_factor
```

### Clarity (ai_modules/clarity.py)
```python
score = 100.0
if words < 5: score -= 50
elif words < 20: score -= (20 - words) × 1.5
if repeated_bigrams > 0: score -= min(20, repeats × 5)
if filler_words > 3: score -= min(15, (fillers - 3) × 3)
if broken_structure: score -= 10
final = clamp(score, 0, 100)
```

### Confidence (ai_modules/behavioral_confidence.py)
```python
video_conf = (0.40×eye + 0.30×head + 0.20×(1-blink/60) + 0.10×(1-stress)) × 100
audio_conf = (0.30×speech_rate + 0.30×pause + 0.25×pitch + 0.15×energy) × 100
text_conf = (1.0 - hesitation_ratio×5) × 100
final = (0.60×video + 0.25×audio + 0.15×text) with normalization if missing
```

### Overall (ai_modules/hierarchical.py)
```python
overall = 0.50 × correctness + 0.30 × clarity + 0.20 × confidence
```

---

## SECURITY MECHANISMS

- **JWT**: HS256, 120min expiry, SECRET_KEY from .env, Bearer scheme
- **Password**: bcrypt (cost 12), never stored plaintext
- **Ownership**: All queries filtered by `user_id == token.user_id`
- **Validation**: Pydantic models (email format, char limits, field clamping)
- **CORS**: Multiple localhost origins (dev) — **MUST restrict in prod**
- **Error Handling**: Global exception handler → 500 with logging, no stack trace leakage

**Vulnerabilities**:
- ❌ No rate limiting
- ❌ No file size limits (DoS vector)
- ⚠️ No HTML sanitization on AI-generated content (XSS possible)
- ⚠️ No audit logging

---

## ERROR HANDLING & FALLBACKS

### AI Service Failures (services/ai_service.py)
**Retry Strategy**: 1 retry with 1s delay, 20s timeout  
**Fallbacks**:
- Groq question gen fails → Return FALLBACK_QUESTIONS (10 generic questions)
- Groq scoring fails → Return {"score": 60, "reason": "estimated"}
- Gemini analysis fails → Return {"score": 70, "summary": "unavailable", ...}
- SBERT fails → Return 60.0 cosine score

### Frontend Graceful Degradation
- MediaPipe fails to load → Disable camera, continue with text-only
- Web Speech API unavailable → Type-only mode
- MediaRecorder fails → Skip audio analysis, use video+text only

### Database Errors
- Duplicate question → 400 "Question already answered"
- Session not found → 404 "Session not found"
- Transaction failure → Rollback + 500 error

---

## IMPORTANT DESIGN DECISIONS

1. **Why Three Independent Dimensions?**
   - Prevents behavioral cues from punishing knowledge (shy expert still scores high on correctness)
   - Allows targeted improvement recommendations per dimension

2. **Why Hybrid Correctness Scoring?**
   - LLM alone is expensive and slow
   - SBERT catches semantic relevance LLM might miss
   - Keyword coverage prevents generic filler answers
   - Ensemble more robust than any single method

3. **Why Client-Side MediaPipe?**
   - Reduces server load (no video upload)
   - Real-time processing (30 FPS impossible via upload)
   - Privacy-preserving (video never leaves browser)

4. **Why FAISS Not Vector DB?**
   - Small dataset per user (<500 chunks typically)
   - No need for distributed search
   - Simplicity (no extra infrastructure)

5. **Why Groq + Gemini Not OpenAI?**
   - Groq: Fastest inference (1.5-3s vs 5-8s for GPT-4)
   - Gemini: Free tier + multimodal future-proofing
   - Diversification: Reduces vendor lock-in

---

## PRODUCTION HARDENING (CHANGES.md)

**Applied Fixes**:
- ✅ SBERT warm-load at startup (avoids 10s cold start on first answer)
- ✅ Retry logic with 1s delay for Groq/Gemini
- ✅ `*_safe()` variants return structured JSON fallbacks
- ✅ Answer validation (3-2000 chars, non-empty)
- ✅ Duplicate question guard
- ✅ Session ownership + status checks
- ✅ Behavioral metrics auto-clamped to valid ranges [0,1]
- ✅ Cached resume analysis (idempotent)
- ✅ Proper logging (asyncio.logging configured)

**Still Missing**:
- ❌ PostgreSQL migration (SQLite dev only)
- ❌ Rate limiting
- ❌ File size limits
- ❌ HTML sanitization
- ❌ Unit/integration tests

---

## PERFORMANCE BENCHMARKS

**Typical Latencies**:
- Resume upload: 500ms-2s (depends on file size + parsing)
- Generate questions: 3-5s (RAG retrieval + Groq generation)
- Submit answer: 3-5s (Groq + Gemini in series)
- Behavior metrics: <100ms (DB insert + rolling window query)
- Dashboard load: 500ms-1s (depends on session count, no pagination)

**Bottlenecks**:
1. Groq API (1.5-3s) — largest contributor
2. Gemini API (2-4s) — explanation generation
3. SBERT encoding (80-120ms) — already optimized

**Optimization Opportunities**:
- Parallelize Groq scoring + Gemini explanation (savings: 2-4s)
- Cache SBERT embeddings for common questions
- Batch behavioral metrics (currently every 2s, could aggregate more)

---

## TESTING STATUS

**Current State**: ❌ NO AUTOMATED TESTS

**What Should Be Tested**:
- Unit tests: ai_modules/* (scoring formulas, fusion logic)
- Integration tests: API endpoints (auth, CRUD, ownership)
- E2E tests: Full interview flow (Playwright/Cypress)
- Performance tests: Concurrent user load (Locust)

**Known Issues**:
- MediaPipe occasionally fails to load on Firefox
- Web Speech API stops after ~30s silence (handled by auto-restart)
- Large PDF uploads (>10MB) can timeout (no progress indicator)

---

## DEPLOYMENT CHECKLIST

**Environment Variables** (.env):
```bash
JWT_SECRET_KEY=<generate with `openssl rand -hex 32`>
GROQ_API_KEY=<get from console.groq.com>
GEMINI_API_KEY=<get from aistudio.google.com>
DATABASE_URL=postgresql://user:pass@host/db  # NOT sqlite in prod
FRONTEND_URL=https://yourdomain.com  # Update CORS
```

**Pre-Deployment**:
1. Run `python migrate.py` (if upgrading from older schema)
2. Test AI API keys (run `backend/services/ai_service.py` directly)
3. Warm-load SBERT (~500MB download first time)
4. Configure PostgreSQL connection pooling
5. **CHANGE CORS `allow_origins`** to production domain only
6. Add rate limiting middleware (e.g., slowapi)
7. Set up HTTPS (Let's Encrypt)
8. Configure Sentry/Prometheus monitoring

**Startup Commands**:
```bash
# Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend
cd frontend
npm run build
npm run preview  # or serve dist/ with nginx
```

**Recommended Stack**:
- Backend: Gunicorn + UVicorn workers (4-8 workers)
- Frontend: Nginx serving static build
- Database: PostgreSQL 14+ with pgvector extension
- Reverse Proxy: Nginx with SSL termination
- Monitoring: Prometheus + Grafana

---

## COMMON ISSUES & SOLUTIONS

**Issue**: "Groq API unavailable after 2 attempts"  
**Solution**: Check `GROQ_API_KEY` in .env, verify API quota at console.groq.com

**Issue**: "Gemini 404 error"  
**Solution**: Model name changed — system auto-detects, but force refresh by deleting `_gemini_model` global

**Issue**: "Speech recognition stops immediately"  
**Solution**: Browser compatibility issue (use Chrome/Edge, not Safari/Firefox on iOS)

**Issue**: "MediaPipe fails to load landmarks"  
**Solution**: Check CDN availability (https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/), firewall may block

**Issue**: "Dashboard slow with many sessions"  
**Solution**: Add pagination to `/dashboard` endpoint (currently fetches all completed sessions)

**Issue**: "SBERT model download stuck"  
**Solution**: First run downloads ~500MB from Hugging Face — check internet, disk space, /tmp/ permissions

---

## CODEBASE CONVENTIONS

**Python**:
- Import groups: stdlib → third-party → local (separated by blank lines)
- Function docstrings: Google style (Args, Returns)
- Private functions: `_underscore_prefix()`
- Error handling: try/except with logging, never bare `except:`

**React**:
- Functional components only (no class components)
- Custom hooks: `use[Name].js`
- State management: useState + useEffect (no Redux)
- Styling: TailwindCSS utility classes (no CSS modules)

**Database**:
- Models: One file per table in `models/`
- Migrations: Manual via `migrate.py` (no Alembic yet)
- Queries: SQLAlchemy ORM (no raw SQL)

**API**:
- Routes: One router per resource domain
- Responses: Always JSON (no HTML)
- Errors: HTTPException with descriptive `detail` string

---

## QUICK REFERENCE

### Critical File Locations
- **Main entry**: `backend/main.py`, `frontend/src/App.jsx`
- **Scoring logic**: `backend/ai_modules/correctness.py`, `clarity.py`, `behavioral_confidence.py`
- **AI service wrapper**: `backend/services/ai_service.py`
- **Session lifecycle**: `backend/routes/session_routes.py`
- **MediaPipe integration**: `frontend/src/components/CameraFeed.jsx`
- **Speech recognition**: `frontend/src/hooks/useSpeechRecognition.js`

### Key Constants
- JWT expiry: 120 minutes
- Answer constraints: 3-2000 characters
- Behavioral metrics interval: 2 seconds
- FAISS chunk size: 300 words
- Top-K retrieval: 5 chunks
- Groq timeout: 20 seconds
- SBERT model: all-MiniLM-L6-v2 (384 dims)
- MediaPipe landmarks: 468 facial points

### Scoring Weights Summary
```
Overall = 50% Correctness + 30% Clarity + 20% Confidence

Correctness = 60% LLM + 25% SBERT + 15% Keyword
Video Confidence = 40% Eye + 30% Head + 20% Blink + 10% Stress
Audio Confidence = 30% Rate + 30% Pause + 25% Pitch + 15% Energy
Multimodal Confidence = 60% Video + 25% Audio + 15% Text
```

---

END OF AI MEMORY FILE
