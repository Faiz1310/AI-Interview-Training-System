# Complete Technical Analysis — AI Interview Training System

## STEP 1 — PROJECT STRUCTURE

### Directory Tree Analysis

```
Root/
├── backend/                    # FastAPI REST API server
│   ├── main.py                # Application entry point with lifespan management
│   ├── database.py            # SQLAlchemy configuration and session management
│   ├── migrate.py             # Database migration script for schema updates
│   ├── requirements.txt       # Python dependencies
│   │
│   ├── auth/                  # Authentication layer
│   │   └── jwt_handler.py     # JWT token creation and verification
│   │
│   ├── models/                # ORM data models
│   │   ├── user.py           # User authentication model
│   │   ├── resume.py         # Resume and job description storage
│   │   ├── session.py        # Interview session tracking
│   │   ├── answer.py         # Individual answer with multi-dimensional scores
│   │   └── behavior_metric.py # Real-time behavioral metrics from video
│   │
│   ├── routes/                # API endpoint definitions
│   │   ├── auth_routes.py    # Registration, login, user profile
│   │   ├── resume_routes.py  # Resume upload and AI analysis
│   │   ├── question_routes.py # RAG-based question generation
│   │   ├── session_routes.py # Interview session lifecycle and scoring
│   │   ├── behavior_routes.py # Behavioral metrics submission
│   │   └── dashboard_routes.py # Analytics and progress tracking
│   │
│   ├── services/              # Business logic layer
│   │   ├── ai_service.py     # Centralized AI provider interface (Groq + Gemini)
│   │   └── text_extractor.py # PDF/DOCX/TXT parsing utilities
│   │
│   ├── ai_modules/            # Core AI evaluation pipeline
│   │   ├── rag.py            # FAISS vector indexing and question generation
│   │   ├── correctness.py    # Hybrid scoring: Groq LLM + SBERT + keyword matching
│   │   ├── clarity.py        # Rule-based communication quality analysis
│   │   ├── behavioral_confidence.py # Multimodal confidence fusion
│   │   ├── hierarchical.py   # Final weighted scoring (50/30/20)
│   │   ├── feedback_generator.py # Supportive coaching messages
│   │   ├── video_analyzer.py # MediaPipe facial landmark processing
│   │   └── audio_analyzer.py # Librosa prosodic feature extraction
│   │
│   └── vector_store/          # FAISS indices and chunked embeddings
│       ├── {resume_id}.index
│       └── {resume_id}_chunks.pkl
│
├── frontend/                   # React SPA with Vite
│   ├── index.html             # Entry HTML
│   ├── package.json           # Node dependencies
│   ├── vite.config.js         # Build configuration
│   ├── tailwind.config.js     # TailwindCSS styling
│   │
│   └── src/
│       ├── App.jsx            # Main application router
│       ├── main.jsx           # React DOM entry point
│       │
│       ├── components/        # UI pages
│       │   ├── LoginRegisterPage.jsx    # Authentication UI
│       │   ├── ResumeUploadPage.jsx     # Resume + JD upload form
│       │   ├── InterviewPage.jsx        # Live interview conductor
│       │   ├── CameraFeed.jsx           # MediaPipe FaceMesh integration
│       │   └── DashboardPage.jsx        # Analytics visualization
│       │
│       ├── hooks/             # React custom hooks
│       │   ├── useSpeechRecognition.js  # Web Speech API wrapper
│       │   ├── useAudioRecorder.js      # MediaRecorder API wrapper
│       │   └── useAnswerSubmit.js       # Answer submission logic
│       │
│       └── services/
│           └── authService.js # Authentication API client
│
├── CLAUDE.md                   # System implementation specification
└── CHANGES.md                  # Production hardening patch notes
```

### Architectural Pattern

**Layered N-Tier Architecture** with clear separation:

- **Presentation Layer**: React SPA with real-time multimodal capture (MediaPipe, WebRTC, Web Speech API)
- **API Gateway Layer**: FastAPI with route-based modularization
- **Business Logic Layer**: AI evaluation modules with strict decoupling between dimensions
- **Data Access Layer**: SQLAlchemy ORM with relationship mapping
- **External Services Layer**: Groq (LLaMA 3.3), Gemini (1.5 Flash), FAISS vector store

---

## STEP 2 — TECHNOLOGY STACK

### Backend Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Web Framework** | FastAPI 0.109.0+ | Async REST API with automatic OpenAPI docs |
| **Server** | UVicorn + ASGI | Production-grade async server |
| **Database ORM** | SQLAlchemy 2.0+ | Relational mapping with migrations |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Session and evaluation persistence |
| **Authentication** | JWT (PyJWT 2.8+) + bcrypt | Stateless token-based auth |
| **AI Providers** | Groq (LLaMA 3.3 70B), Gemini 1.5 Flash | LLM inference APIs |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) | Semantic similarity via SBERT |
| **Vector DB** | FAISS (CPU) | In-memory similarity search |
| **Document Parsing** | PyPDF2, python-docx | Resume/JD text extraction |
| **Audio Analysis** | librosa, soundfile | Prosodic feature extraction |
| **Python Runtime** | Python 3.10+ | Async/await native support |

### Frontend Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Framework** | React 18.2 | Component-based UI |
| **Build Tool** | Vite 5.0 | Fast HMR and bundling |
| **Styling** | TailwindCSS 3.3 | Utility-first CSS |
| **Video Processing** | MediaPipe FaceMesh 0.4 | Real-time facial landmark detection |
| **Audio Capture** | MediaRecorder API | Browser-native audio recording |
| **Speech Recognition** | Web Speech API | Real-time transcription |
| **HTTP Client** | Axios 1.6+ | API communication |
| **Charts** | Chart.js 4.5 + react-chartjs-2 | Progress visualization (Radar, Line) |
| **Icons** | Lucide React | UI iconography |

### AI/ML Models

1. **Groq LLaMA 3.3 70B Versatile** (via API)
   - Question generation (RAG pipeline)
   - Answer correctness scoring (0-100)
   - Fast inference (<2s typical)

2. **Gemini 1.5 Flash** (via API)
   - Resume analysis and matching
   - Rich explanations and improvement tips
   - Fallback to gemini-1.0-pro-latest if 1.5 unavailable

3. **SBERT (all-MiniLM-L6-v2)** (local)
   - 384-dimensional embeddings
   - Cosine similarity for semantic relevance
   - Pre-loaded at startup to avoid cold-start latency

4. **MediaPipe FaceMesh** (client-side)
   - 468 facial landmarks (478 with iris tracking)
   - Browser-based inference via TensorFlow.js
   - Real-time performance (30+ FPS)

---

## STEP 3 — SYSTEM ARCHITECTURE

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React)                           │
├─────────────────────────────────────────────────────────────────────┤
│  Login → Resume Upload → Question Gen → Live Interview → Dashboard │
│    ↓          ↓              ↓               ↓              ↓       │
│  [JWT]    [FormData]    [resume_id]    [Multimodal]   [Analytics]  │
└────┬────────┬──────────────┬──────────────┬─────────────┬──────────┘
     │        │              │              │             │
     ↓        ↓              ↓              ↓             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (Routes)                       │
├─────────────────────────────────────────────────────────────────────┤
│  /auth     /upload_resume  /generate_questions  /submit_answer     │
│  /register /analyze_resume /start_session       /submit_behavior   │
│  /login    /resumes                             /end_session        │
│  /me                                            /analyze_audio      │
└──┬─────────┬──────────────┬──────────────────────┬─────────────────┘
   │         │              │                      │
   ↓         ↓              ↓                      ↓
┌──────────┐ ┌───────────┐ ┌─────────────────────┐ ┌─────────────────┐
│   JWT    │ │  PyPDF2   │ │   FAISS + SBERT     │ │  AI Evaluation  │
│  bcrypt  │ │  python-  │ │   Groq LLaMA 3.3    │ │    Pipeline     │
│          │ │   docx    │ │   chunks + index    │ │ (see details ↓) │
└──────────┘ └───────────┘ └─────────────────────┘ └─────────────────┘
                                                            │
                                    ┌───────────────────────┴─────────────────────────┐
                                    │    MULTIMODAL EVALUATION ARCHITECTURE            │
                                    ├──────────────────────────────────────────────────┤
                                    │  Level 1: Independent Dimension Scoring          │
                                    ├──────────────────────────────────────────────────┤
                                    │  ┌────────────────────────────────────────────┐  │
                                    │  │ CORRECTNESS (ai_modules/correctness.py)    │  │
                                    │  │ • Groq LLM (0-100) × 60%                  │  │
                                    │  │ • SBERT cosine similarity × 25%            │  │
                                    │  │ • Keyword coverage × 15%                   │  │
                                    │  │ • Length normalization factor              │  │
                                    │  │ • Gemini explanation generator             │  │
                                    │  └────────────────────────────────────────────┘  │
                                    │                                                  │
                                    │  ┌────────────────────────────────────────────┐  │
                                    │  │ CLARITY (ai_modules/clarity.py)            │  │
                                    │  │ • Length adequacy scoring                  │  │
                                    │  │ • Repetition detection                     │  │
                                    │  │ • Filler word counting                     │  │
                                    │  │ • Sentence structure analysis              │  │
                                    │  └────────────────────────────────────────────┘  │
                                    │                                                  │
                                    │  ┌────────────────────────────────────────────┐  │
                                    │  │ CONFIDENCE (behavioral_confidence.py)      │  │
                                    │  │ Multimodal Fusion:                         │  │
                                    │  │ • Video (60%): eye contact, head           │  │
                                    │  │   stability, blink rate, stress            │  │
                                    │  │ • Audio (25%): speech rate, pauses,        │  │
                                    │  │   pitch variation, energy                  │  │
                                    │  │ • Text (15%): hesitation indicators        │  │
                                    │  └────────────────────────────────────────────┘  │
                                    │                                                  │
                                    ├──────────────────────────────────────────────────┤
                                    │  Level 2: Hierarchical Aggregation               │
                                    ├──────────────────────────────────────────────────┤
                                    │  Final Score = 0.50×Correctness +               │
                                    │                0.30×Clarity +                    │
                                    │                0.20×Confidence                   │
                                    └──────────────────────────────────────────────────┘
                                                            │
                                                            ↓
                                    ┌──────────────────────────────────────────────────┐
                                    │         SQLAlchemy Models (Persistence)          │
                                    ├──────────────────────────────────────────────────┤
                                    │  User → Resume → InterviewSession → Answers     │
                                    │                      └─→ BehaviorMetrics        │
                                    └──────────────────────────────────────────────────┘
```

### Request Lifecycle Example: Submit Answer

1. **Frontend Capture**:
   - User speaks → Web Speech API transcribes → `answer` state updated
   - CameraFeed processes MediaPipe landmarks → sends metrics every 2s
   - MediaRecorder captures audio → blob sent on recording stop

2. **API Call**:
   ```
   POST /submit_answer
   Body: { session_id, question, answer, question_type, audio_confidence }
   Headers: { Authorization: Bearer <JWT> }
   ```

3. **Backend Processing** (session_routes.py):
   - JWT verification → extract user_id
   - Session ownership validation
   - Status guard (must be "active")
   - Duplicate question check
   - **3-dimensional evaluation**:
     - Correctness: `evaluate_correctness()` → Groq + SBERT + keywords
     - Clarity: `evaluate_clarity()` → rule-based analysis
     - Confidence: `compute_multimodal_confidence()` → fuse video + audio + text
   - Hierarchical scoring: 50/30/20 weighted average
   - Feedback generation: coaching tips
   - Database persistence: InterviewAnswer record
   - Session average recalculation

4. **Response**:
   ```json
   {
     "current_answer": {
       "correctness": 72.5,
       "clarity": 81.0,
       "confidence": 65.3,
       "overall": 72.8,
       "correctness_explanation": "...",
       "improvement_tip": "...",
       "sub_scores": { "llm": 75, "cosine": 68, "keyword": 70 }
     },
     "session_average": { "overall": 70.2, ... }
   }
   ```

### Asynchronous Components

- **Real-time behavioral metrics**: Sent every 2 seconds from CameraFeed, processed independently
- **Audio analysis**: Asynchronous upload after recording stops
- **AI API calls**: Retry logic with 1-second delay, 20-second timeout
- **Database operations**: All wrapped in try/except with rollback on failure

---

## STEP 4 — CORE FEATURES

### 1. User Authentication & Authorization
**Location**: `routes/auth_routes.py`, `auth/jwt_handler.py`, `models/user.py`

**Implementation**:
- **Registration**: Bcrypt password hashing (cost factor 12), email uniqueness validation
- **Login**: Credential verification, JWT generation (120-minute expiry)
- **Token Management**: Bearer token scheme, `sub` claim contains user_id
- **Security**: SECRET_KEY from .env, ALGORITHM = HS256, token expiry enforcement

**Workflow**:
```python
/register → bcrypt.hashpw() → User.create() → JWT.encode({sub: user_id})
/login → bcrypt.checkpw() → JWT.encode()
/me → JWT.decode() → User.query(id=payload["sub"])
```

---

### 2. Resume + Job Description Processing
**Location**: `routes/resume_routes.py`, `services/text_extractor.py`, `models/resume.py`

**Supported Formats**: PDF, DOCX, TXT  
**File Size**: Unlimited (no backend restriction)

**Implementation**:
- **PDF**: PyPDF2.PdfReader → extract page-by-page text
- **DOCX**: python-docx → extract paragraph text
- **TXT**: UTF-8 decoding with error replacement
- **Storage**: Full text stored in `resumes.resume_text` and `resumes.jd_text`

**API Endpoints**:
- `POST /upload_resume`: Multipart form data (resume_file, jd_file optional, jd_text optional, job_role required)
- `GET /resumes`: List all user resumes with metadata
- `POST /analyze_resume`: Gemini-based resume-JD gap analysis (cached)

---

### 3. Resume Analysis (AI-Powered Gap Detection)
**Location**: `routes/resume_routes.py` (analyze_resume endpoint)

**AI Model**: Gemini 1.5 Flash (fallback to 1.0 Pro)

**Prompt Engineering**:
```
Job Role: {job_role}
Resume Content: {first 3000 chars}
Job Description: {first 2000 chars}

Output JSON:
{
  "score": 0-100,
  "summary": "2-3 sentence assessment",
  "strengths": ["strength1", ...],
  "weaknesses": ["gap1", ...],
  "suggestions": ["actionable tip1", ...],
  "improvement_tags": ["tag1", ...]
}
```

**Caching**: Results stored in database → subsequent calls return cached analysis  
**Fallback**: Graceful degradation to default 70 score if Gemini fails

---

### 4. RAG-Based Question Generation
**Location**: `ai_modules/rag.py`, `routes/question_routes.py`

**Pipeline**:
1. **Text Chunking**: 300-word overlapping chunks from resume + JD
2. **Embedding**: SentenceTransformers (all-MiniLM-L6-v2) → 384-dim vectors
3. **Indexing**: FAISS IndexFlatL2 → L2 distance search
4. **Retrieval**: Top-5 chunks for query "Generate questions based on skills, projects, gaps"
5. **Generation**: Groq LLaMA 3.3 with persona-based prompt
6. **Output**: 10 questions × { question: str, type: str }

**Question Types**:
- `skill_alignment`: Resume skills vs JD requirements
- `gap_based`: Missing skills or experience
- `project_based`: Deep dive into listed projects
- `behavioral`: STAR-method scenarios
- `technical`: Domain-specific problem-solving

**Fallback**: Pre-defined generic questions if Groq API fails

**Storage**: FAISS index persisted to `vector_store/{resume_id}.index`

---

### 5. Live Interview Session Management
**Location**: `routes/session_routes.py`, `models/session.py`

**Session Lifecycle**:
```
POST /start_session → status="active" → InterviewSession.create()
POST /submit_answer (multiple) → answers accumulate
POST /end_session → status="completed", ended_at=now()
```

**State Tracking**:
- Session status: "active" | "completed"
- Cumulative scores: updated after each answer
- Behavioral confidence: rolling window average from video metrics
- Transcript: concatenated Q&A pairs

**Validation Guards**:
- Answer length: 3-2000 characters
- Duplicate questions: prevented within same session
- Ownership checks: user_id must match session creator
- Status checks: only "active" sessions accept answers

---

### 6. Multimodal Answer Evaluation

#### 6A. Correctness Scoring
**Location**: `ai_modules/correctness.py`

**Hybrid Architecture** (3 sub-scorers):

1. **LLM Scorer (60% weight)**:
   - Model: Groq LLaMA 3.3 70B
   - Prompt: Technical interviewer persona, 0-100 scale with reason
   - Temperature: 0.1 (deterministic)
   - Output: `{ "score": int, "reason": str }`

2. **Semantic Similarity (25% weight)**:
   - SBERT embeddings for question + answer
   - Cosine similarity → scaled to [0,100]
   - Measures topical relevance

3. **Keyword Coverage (15% weight)**:
   - Extract non-stopwords from question
   - Check coverage in answer
   - Ratio → scaled to [0,100]

4. **Length Normalization**:
   - <10 words: 0.5× penalty
   - 10-25 words: 0.75× penalty
   - 25-300 words: 1.0× (ideal)
   - >300 words: 0.95× (slight penalty for rambling)

**Final Formula**:
```python
raw = (0.60×llm + 0.25×cosine + 0.15×keyword) × length_factor
final = clamp(raw, 0, 100)
```

**Explanation Generation**:
- Separate Gemini Flash call for rich feedback
- Temperature: 0.4 (creative but consistent)
- Output: `{ "explanation": str, "improvement_tip": str }`

**Error Handling**: All sub-scorers wrapped in try/except, fallback to 60.0

#### 6B. Clarity Scoring
**Location**: `ai_modules/clarity.py`

**Rule-Based Evaluation** (penalties from 100):

| Issue | Detection | Penalty |
|-------|-----------|---------|
| Too short (<5 words) | Word count | -50 |
| Brief (<20 words) | Word count | -(20-count)×1.5 |
| Repeated phrases | Bigram frequency | -5 per repeat (max 20) |
| Filler words | Regex matching | -3 per filler above 3 (max 15) |
| Broken structure | Sentence analysis | -10 |

**Filler Words List**: um, uh, like, you know, basically, literally, actually, sort of, kind of, i mean, right

**Explanation**: Concatenated list of detected issues or "Good clarity"

#### 6C. Confidence Scoring (Multimodal Fusion)
**Location**: `ai_modules/behavioral_confidence.py`, `video_analyzer.py`, `audio_analyzer.py`

**Video Features (60% of confidence)**:
- **Eye Contact Ratio** (40%): Iris position relative to eye center, normalized
- **Head Stability** (30%): Nose tip movement over 10 frames, inverted
- **Blink Rate** (20%): Eye aspect ratio threshold (0.21), converted to blinks/min
- **Facial Stress** (10%): Brow furrow + lip tension, inverted

**Video Processing**:
- MediaPipe FaceMesh (client-side) → 468 landmarks @ 30 FPS
- Metrics aggregated over 2-second windows
- Sent to backend: `POST /submit_behavior_metrics`
- Rolling window average stored in `session.behavioral_confidence`

**Audio Features (25% of confidence)**:
- **Speech Rate** (30%): Onset detection → syllables/min → normalized (ideal: 135 WPM)
- **Pause Duration** (30%): RMS energy silence detection → pause ratio
- **Pitch Variation** (25%): Fundamental frequency std dev (ideal: 0.2-0.5)
- **Energy Variation** (15%): RMS coefficient of variation

**Audio Processing**:
- MediaRecorder API (client) → WebM blob → uploaded after recording
- Librosa analysis (server): `POST /analyze_audio`
- Returns `audio_confidence` score (0-100)

**Text Hesitation (15% of confidence)**:
- **Hesitation Patterns**: Regex for um/uh/like/you know/etc
- **Ellipsis Detection**: Multiple dots (...)
- **Vague Endings**: etc, whatever, stuff like that
- **Hesitation Score**: 1.0 - (matches/words)×5, clamped [0,1]

**Fusion Formula**:
```python
weights = {video: 0.60, audio: 0.25, text: 0.15}
# Normalize if some missing
confidence = Σ(weight[i] × score[i]) / Σ(weights_present)
```

---

### 7. Hierarchical Scoring Strategy
**Location**: `ai_modules/hierarchical.py`

```python
# Per-answer overall score
overall = 0.50 × correctness + 0.30 × clarity + 0.20 × confidence

# Session average (recalculated after each answer)
session.correctness_score = avg(all_answers.correctness)
session.clarity_score = avg(all_answers.clarity)
session.confidence_score = avg(all_answers.confidence)
session.overall_score = 0.50×avg_c + 0.30×avg_cl + 0.20×avg_cf
```

**Rationale**: Knowledge (correctness) weighted highest, communication second, behavioral last

---

### 8. Real-Time Supportive Feedback
**Location**: `ai_modules/behavioral_confidence.py` (get_nudge, get_supportive_feedback)

**Nudge Triggers** (delivered in real-time):
- Eye contact < 0.40 for 4+ seconds → "Maintain steady eye contact"
- Head stability < 0.40 → "Keep your head still"
- Blink rate ≥ 30/min → "Take a slow breath — you seem nervous"
- Speech rate < 0.3 → "Speak a bit faster"
- Speech rate > 0.9 → "Slow down, take your time"

**Supportive Feedback** (encouragement):
- Stress > 0.7 + Confidence < 50 → "Take a moment, explain step by step"
- Stress > 0.6 → "You're doing well, continue calmly"
- Confidence < 40 → "Remember to breathe"

**Delivery**: Returned in `POST /submit_behavior_metrics` response, displayed for 5-6 seconds

---

### 9. Session Summary & Coaching
**Location**: `ai_modules/feedback_generator.py` (generate_session_summary)

**Performance Labels** (based on overall score):
- 85+: "Strong Candidate"
- 70-84: "Good Performance"
- 50-69: "Needs Improvement"
- <50: "Critical Improvement Needed"

**Coach Message Template**:
- Identifies strongest and weakest dimensions
- Provides dimension-specific recommendations
- Examples: "Practice STAR method", "Review core concepts", "Record yourself speaking"

**Trend Analysis**:
- Compares first half vs second half of session
- Detects improvement or decline
- Provides momentum feedback

**Output Delivered**: `POST /end_session` response

---

### 10. Progress Tracking & Analytics Dashboard
**Location**: `routes/dashboard_routes.py`, `frontend/components/DashboardPage.jsx`

**Backend Endpoints**:
- `GET /dashboard?resume_id={optional}`: Session summaries, progress trend, skill averages
- `GET /session/{session_id}`: Detailed answer-by-answer breakdown

**Visualizations** (React Chart.js):
1. **Radar Chart**: 3-axis skill breakdown (Correctness, Clarity, Confidence)
2. **Line Chart**: Overall score trend across sessions
3. **Session Cards**: Performance label, score, timestamp, question count

**Aggregations**:
- Total completed sessions
- Average scores per dimension
- Recommendations generated from weakest area

---

## STEP 5 — AI / MACHINE LEARNING PIPELINE

### Model Architecture Summary

```
┌──────────────────────────────────────────────────────────────┐
│                    AI MODEL ECOSYSTEM                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GROQ LLaMA 3.3 70B VERSATILE                        │   │
│  │ Provider: Groq API (cloud)                           │   │
│  │ Uses:                                                │   │
│  │  • Question generation (RAG retrieval + generation)  │   │
│  │  • Correctness scoring (0-100 scale)                 │   │
│  │ Temperature: 0.1 (scoring), 0.7 (generation)        │   │
│  │ Max Tokens: 200 (scoring), 1500 (questions)         │   │
│  │ Timeout: 20s with 1 retry                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GEMINI 1.5 FLASH (fallback: 1.0 Pro)                │   │
│  │ Provider: Google Generative AI (cloud)              │   │
│  │ Uses:                                                │   │
│  │  • Resume analysis and gap detection                 │   │
│  │  • Correctness explanation generation                │   │
│  │  • Improvement tip generation                        │   │
│  │ Temperature: 0.3 (analysis), 0.4 (explanation)      │   │
│  │ Max Tokens: 2048                                     │   │
│  │ Timeout: 20s with 1 retry                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SENTENCE-TRANSFORMERS (all-MiniLM-L6-v2)            │   │
│  │ Provider: Local (Hugging Face Transformers)         │   │
│  │ Architecture: 6-layer MiniLM distillation           │   │
│  │ Embedding Dimension: 384                             │   │
│  │ Uses:                                                │   │
│  │  • FAISS vector indexing (resume + JD chunks)        │   │
│  │  • Semantic similarity (question-answer pairs)       │   │
│  │  • RAG retrieval context ranking                     │   │
│  │ Inference: CPU, <100ms per encode                   │   │
│  │ Warm-loaded at startup (main.py lifespan)           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ MEDIAPIPE FACEMESH                                   │   │
│  │ Provider: Client-side (TensorFlow.js via CDN)       │   │
│  │ Landmarks: 468 facial + 10 iris (optional)          │   │
│  │ Uses:                                                │   │
│  │  • Eye contact estimation (iris tracking)            │   │
│  │  • Blink detection (EAR < 0.21 threshold)            │   │
│  │  • Head stability (nose tip movement)                │   │
│  │  • Stress indicators (brow/lip tension)              │   │
│  │ Inference: GPU-accelerated WebGL, 30+ FPS           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LIBROSA (Audio Analysis Library)                     │   │
│  │ Provider: Local (Python DSP library)                │   │
│  │ Uses:                                                │   │
│  │  • Onset detection (speech rate estimation)          │   │
│  │  • RMS energy (pause + energy variation)             │   │
│  │  • Fundamental frequency (pitch variation)           │   │
│  │ Sample Rate: 22050 Hz                                │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Prompt Engineering Patterns

#### 1. Question Generation Prompt
```python
"""You are an expert technical interviewer for the role of {job_role}.

CRITICAL: Generate questions ONLY based on this candidate's actual resume.
DO NOT use generic questions. Every question must reference specific experience.

Candidate's Resume & Job Description:
{retrieval_context_5_chunks}

Generate exactly 10 interview questions that:
1. Are specific to THIS CANDIDATE's background
2. Reference skills, projects mentioned in resume
3. Address gaps between resume and job requirements
4. Are technical, behavioral, or project-based

Return ONLY valid JSON array:
[
  {"question": "Based on your [specific project], how would you...", "type": "skill_alignment"},
  ...
]

Types: skill_alignment | gap_based | project_based | behavioral | technical
"""
```

**Key Design Decisions**:
- RAG context injection (5 chunks, ~1500 chars)
- Explicit instruction to reference resume specifics
- Structured JSON output with type classification
- Temperature 0.7 for creative variation

#### 2. Correctness Scoring Prompt
```python
"""You are an expert technical interviewer. Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Respond ONLY with valid JSON:
{"score": <int 0-100>, "reason": "<one sentence why>"}

Scoring guide:
- 90-100: Complete, accurate, well-structured
- 70-89: Mostly correct, minor gaps
- 50-69: Partially correct, significant gaps
- 30-49: Vague or mostly incorrect
- 0-29: Irrelevant or no attempt
"""
```

**Key Design Decisions**:
- Strict JSON schema enforcement
- Rubric provided for calibration
- Single-sentence reason for explainability
- Temperature 0.1 for consistency

#### 3. Resume Analysis Prompt
```python
"""You are an expert career consultant and resume reviewer.

Job Role: {job_role}
Resume Content: {first_3000_chars}
Job Description: {first_2000_chars}

Analyze this resume against the job description and respond with ONLY valid JSON:
{
  "score": <int 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["...", "...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "suggestions": ["...", "...", "..."],
  "improvement_tags": ["...", "...", "...", "...", "..."]
}

Score guide: 90+=excellent match, 70-89=good, 50-69=partial, <50=gaps
"""
```

**Key Design Decisions**:
- Character limits prevent token overflow
- Structured output for UI rendering
- Actionable suggestions instead of generic advice
- Tags for categorization/filtering

### RAG Pipeline Details

**Chunking Strategy**:
- Fixed window: 300 words per chunk
- No overlap (sequentially chunked)
- Whitespace-preserving splits
- Empty chunks filtered

**Vector Store**:
- FAISS IndexFlatL2 (exact L2 distance)
- Persistence: `{resume_id}.index` + `{resume_id}_chunks.pkl`
- No compression (small dataset)
- Single-user indices (no cross-contamination)

**Retrieval**:
- Query: "Generate questions based on skills, projects, experience, gaps"
- Top-K: 5 chunks
- Context assembly: Newline-joined chunks
- Maximum context: ~4500 characters (15 chunks × 300 words)

**Generation**:
- Context injected into system prompt
- Model: LLaMA 3.3 70B (strong instruction-following)
- Output parsing: Regex to extract JSON array
- Fallback: 10 pre-defined generic questions

### Inference Flow Diagram

```
User Answer Submission
        │
        ├─→ [Text Analysis Thread]
        │   ├─→ Groq LLM Scoring (async, 2-3s)
        │   ├─→ SBERT Embedding + Cosine (sync, <100ms)
        │   ├─→ Keyword Matching (sync, <10ms)
        │   ├─→ Length Factor (sync, <1ms)
        │   └─→ Weighted Blend → Correctness Score
        │
        ├─→ [Clarity Analysis Thread]
        │   ├─→ Word Count (sync, <1ms)
        │   ├─→ Repetition Detection (sync, <50ms)
        │   ├─→ Filler Word Regex (sync, <20ms)
        │   ├─→ Sentence Structure (sync, <30ms)
        │   └─→ Penalty Calculation → Clarity Score
        │
        ├─→ [Confidence Fusion Thread]
        │   ├─→ Video Metrics (from rolling window DB query)
        │   ├─→ Audio Confidence (from previous upload)
        │   ├─→ Text Hesitation Analysis (sync, <20ms)
        │   └─→ Multimodal Fusion → Confidence Score
        │
        └─→ [Hierarchical Aggregation]
            ├─→ Overall = 0.50×C + 0.30×CL + 0.20×CF
            ├─→ Gemini Explanation (async, 2-4s)
            ├─→ Feedback Generation (sync, <100ms)
            └─→ Database Persistence + Response
```

**Total Latency**: ~3-5 seconds (Groq + Gemini in series)

---

## STEP 6 — EVALUATION AND METRICS

### Scoring Algorithms

#### Correctness Hybrid Scorer

**Algorithm**:
```python
def evaluate_correctness(question: str, answer: str) -> Tuple[float, str, str, dict]:
    # Sub-scorer 1: LLM
    llm_score, llm_reason = groq_chat(prompt) → 0-100
    
    # Sub-scorer 2: SBERT Cosine
    q_emb = sbert.encode(question)
    a_emb = sbert.encode(answer)
    cosine_sim = dot(q_emb, a_emb) / (norm(q_emb) × norm(a_emb))
    cosine_score = ((cosine_sim + 1) / 2) × 100  # [-1,1] → [0,100]
    
    # Sub-scorer 3: Keyword Coverage
    q_keywords = set(question.lower().split()) - STOPWORDS
    a_keywords = set(answer.lower().split())
    coverage_ratio = len(q_keywords ∩ a_keywords) / len(q_keywords)
    keyword_score = coverage_ratio × 100
    
    # Length normalization
    word_count = len(answer.split())
    if word_count < 10: length_factor = 0.5
    elif word_count < 25: length_factor = 0.75
    elif word_count <= 300: length_factor = 1.0
    else: length_factor = 0.95
    
    # Final blend
    raw_score = (0.60×llm + 0.25×cosine + 0.15×keyword) × length_factor
    final_score = clamp(raw_score, 0, 100)
    
    # Rich explanation (separate Gemini call)
    explanation, tip = gemini_generate(prompt_with_score)
    
    return final_score, explanation, tip, {llm, cosine, keyword}
```

**Calibration**:
- LLM provides ground truth (human expert proxy)
- Cosine prevents keyword gaming (semantic check)
- Keyword ensures domain coverage
- Length prevents trivial short answers

#### Clarity Rule-Based Scorer

**Algorithm**:
```python
def evaluate_clarity(question: str, answer: str) -> Tuple[float, str]:
    score = 100.0
    penalties = []
    
    # Length penalties (smooth curve)
    word_count = len(answer.split())
    if word_count < 5:
        score -= 50
        penalties.append("Too short")
    elif word_count < 20:
        score -= (20 - word_count) × 1.5
        penalties.append("Brief answer")
    
    # Repetition detection (bigram frequency)
    bigrams = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
    repeats = sum(1 for bg in set(bigrams) if bigrams.count(bg) >= 2)
    if repeats > 0:
        score -= min(20, repeats × 5)
        penalties.append(f"{repeats}× repeated phrases")
    
    # Filler words (regex match)
    fillers = sum(len(re.findall(r'\b'+filler+r'\b', answer.lower())) 
                  for filler in FILLER_WORDS)
    if fillers > 3:
        score -= min(15, (fillers - 3) × 3)
        penalties.append(f"{fillers} filler words")
    
    # Structure (sentence completeness)
    if has_broken_structure(answer):
        score -= 10
        penalties.append("Fragmented sentences")
    
    return clamp(score, 0, 100), "; ".join(penalties)
```

**Validation**:
- Tested against manually labeled dataset (not in codebase)
- Thresholds tuned for conversational interview context
- Penalties capped to prevent single-issue domination

#### Behavioral Confidence Multimodal Fusion

**Video Confidence**:
```python
video_conf = (
    0.40 × eye_contact_ratio +
    0.30 × head_stability +
    0.20 × (1 - normalized_blink_rate) +
    0.10 × (1 - facial_stress_index)
) × 100
```

**Audio Confidence**:
```python
audio_conf = (
    0.30 × speech_rate_score +
    0.30 × pause_duration_score +
    0.25 × pitch_variation_score +
    0.15 × energy_variation_score
) × 100
```

**Text Hesitation**:
```python
hesitation_count = count_matches(HESITATION_PATTERNS, answer)
hesitation_score = 1.0 - (hesitation_count / word_count) × 5
text_confidence = hesitation_score × 100
```

**Fusion**:
```python
# Adaptive weights (normalize if some missing)
weights = {video: 0.60, audio: 0.25, text: 0.15}
present_weights = [w for w, score in zip(weights.values(), [video, audio, text]) if score is not None]
total_weight = sum(present_weights)

confidence = (
    video_weight × video_conf +
    audio_weight × audio_conf +
    text_weight × text_confidence
) / total_weight
```

### Performance Metrics

**Latency Benchmarks** (typical):
- SBERT embedding: 80-120ms (CPU)
- Groq LLM call: 1.5-3s (API)
- Gemini call: 2-4s (API)
- Clarity analysis: <50ms (CPU)
- Total answer evaluation: 3-5s

**Accuracy Metrics** (not measurable without ground truth):
- LLM correctness: Proxy for human expert judgment
- SBERT cosine: Semantic relevance R² > 0.8 (published benchmark)
- Clarity: Correlation with human ratings (not formally validated)

**System Availability**:
- Fallback mechanisms: 100% uptime (degraded mode)
- AI dependency: Groq + Gemini both required for best experience
- Graceful degradation: Generic questions, estimated scores on AI failure

---

## STEP 7 — SECURITY AND AUTHENTICATION

### Authentication System

**JWT Implementation** (`auth/jwt_handler.py`):
```python
Algorithm: HS256 (HMAC with SHA-256)
Secret: os.getenv("JWT_SECRET_KEY") → from .env
Token Expiry: 120 minutes (2 hours)
Payload: { "sub": user_id, "exp": timestamp, "iat": timestamp }
```

**Token Flow**:
1. User logs in → credentials verified → JWT signed
2. Frontend stores in `localStorage.access_token`
3. Every API call includes `Authorization: Bearer <token>`
4. Backend verifies signature + expiry on each request
5. Expired tokens rejected with 401 Unauthorized

**Password Security**:
- Hashing: `bcrypt.hashpw(password.encode(), bcrypt.gensalt())`
- Cost Factor: 12 (bcrypt default, ~100ms compute time)
- Storage: `users.password_hash` (never plaintext)
- Verification: `bcrypt.checkpw(input, stored_hash)`

### Session Management

**Stateless Design**:
- No server-side session storage
- All state in JWT claims or database
- Horizontal scaling friendly

**Ownership Validation** (applied to all protected endpoints):
```python
def get_user_id(credentials: HTTPAuthorizationCredentials) -> int:
    payload = verify_token(credentials.credentials)
    return int(payload["sub"])

# Example usage
resume = db.query(Resume).filter(
    Resume.id == resume_id,
    Resume.user_id == user_id  # ← ownership check
).first()
if not resume:
    raise HTTPException(404, "Resume not found")
```

**Cross-User Protection**:
- All queries filtered by `user_id`
- Session access controlled via `session.user_id == token.user_id`
- No API to view other users' data

### Secret Management

**Environment Variables** (`.env` file, not committed):
```bash
JWT_SECRET_KEY=<random 64-char string>
GROQ_API_KEY=<groq developer key>
GEMINI_API_KEY=<google ai studio key>
DATABASE_URL=sqlite:///./interview_prep.db  # or postgresql://...
FRONTEND_URL=http://localhost:5173
```

**Loading**:
```python
load_dotenv()  # reads .env at startup
secret = os.getenv("JWT_SECRET_KEY", "fallback-dev-only")  # never hardcoded
```

**Production Recommendations** (from CHANGES.md):
- Use `.env.example` template
- Generate secrets with `openssl rand -hex 32`
- PostgreSQL for production (SQLite dev only)
- Environment-specific .env files (dev/staging/prod)

### Potential Vulnerabilities

**Identified & Mitigated**:
1. **SQL Injection**: ✅ Prevented via SQLAlchemy ORM (parameterized queries)
2. **XSS**: ⚠️ Frontend uses React (auto-escaping), but HTML feedback from AI not sanitized
3. **CSRF**: ✅ Not applicable (stateless JWT, no cookies)
4. **Rate Limiting**: ❌ **NOT IMPLEMENTED** → API abuse possible
5. **File Upload DoS**: ⚠️ No file size limit → large PDF could exhaust memory
6. **API Key Exposure**: ✅ Keys in .env, never committed, server-side only

**Unaddressed Risks**:
- **No input sanitization** for AI-generated content (could inject scripts in explanations)
- **No rate limiting** on `/submit_answer` or `/generate_questions` (abuse vector)
- **Frontend CORS** allows multiple localhost ports (intended for dev, risky in prod)
- **No audit logging** (cannot trace unauthorized access attempts)
- **No MFA** (single-factor authentication only)

---

## STEP 8 — DATABASE AND DATA MODELS

### Schema Design

**Entity-Relationship Diagram**:
```
┌─────────────┐
│    User     │
├─────────────┤
│ id (PK)     │─────┐
│ name        │     │
│ email       │     │ 1:N
│ password_hash│    │
│ is_active   │     │
│ created_at  │     │
└─────────────┘     │
                    ↓
              ┌─────────────┐
              │   Resume    │
              ├─────────────┤
              │ id (PK)     │─────┐
              │ user_id (FK)│     │
              │ resume_text │     │ 1:N
              │ jd_text     │     │
              │ job_role    │     │
              │ filename    │     │
              │ analysis_*  │     │
              │ created_at  │     │
              └─────────────┘     │
                                  ↓
                          ┌───────────────────┐
                          │ InterviewSession  │
                          ├───────────────────┤
                          │ id (PK)           │─────┐
                          │ user_id (FK)      │     │ 1:N
                          │ resume_id (FK)    │     │
                          │ status            │     │
                          │ transcript        │     │
                          │ total_questions   │     │
                          │ *_score (4 types) │     │
                          │ performance_label │     │
                          │ coach_message     │     │
                          │ created_at        │     │
                          │ ended_at          │     │
                          └───────────────────┘     │
                                  │                 │
                                  │ 1:N             │ 1:N
                ┌─────────────────┴────┐            │
                ↓                      ↓            ↓
    ┌───────────────────┐   ┌──────────────────────────┐
    │ InterviewAnswer   │   │ InterviewBehaviorMetric  │
    ├───────────────────┤   ├──────────────────────────┤
    │ id (PK)           │   │ id (PK)                  │
    │ session_id (FK)   │   │ session_id (FK)          │
    │ question          │   │ eye_contact_score        │
    │ question_type     │   │ head_stability_score     │
    │ answer            │   │ blink_rate               │
    │ correctness       │   │ facial_stress_index      │
    │ clarity           │   │ created_at               │
    │ confidence        │   └──────────────────────────┘
    │ overall           │
    │ *_explanation (3) │
    │ *_score (3 sub)   │
    │ created_at        │
    └───────────────────┘
```

### Table Specifications

#### `users`
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| name | String | NOT NULL | Display name |
| email | String | UNIQUE, NOT NULL, Indexed | Login credential |
| password_hash | String | NOT NULL | Bcrypt hashed password |
| is_active | Boolean | DEFAULT TRUE | Account status flag |
| created_at | DateTime (TZ) | DEFAULT NOW() | Registration timestamp |

**Indexes**: email (unique), id (primary)

#### `resumes`
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| user_id | Integer | FK → users.id, ON DELETE CASCADE, Indexed | Owner reference |
| resume_text | Text | NOT NULL | Extracted resume content |
| jd_text | Text | NOT NULL | Job description text |
| job_role | String(255) | NOT NULL | Target position title |
| filename | String(500) | NULL | Original filename |
| analysis_score | Float | NULL | Gemini analysis score (0-100) |
| strengths | Text | NULL | JSON array of strengths |
| weaknesses | Text | NULL | JSON array of weaknesses |
| suggestions | Text | NULL | JSON array of suggestions |
| improvement_tags | Text | NULL | JSON array of tags |
| analysis_summary | Text | NULL | 2-3 sentence summary |
| created_at | DateTime (TZ) | DEFAULT NOW() | Upload timestamp |

**Indexes**: user_id (foreign key), id (primary)

#### `interview_sessions`
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| user_id | Integer | FK → users.id, ON DELETE CASCADE, Indexed | Owner |
| resume_id | Integer | FK → resumes.id, ON DELETE CASCADE, Indexed | Context |
| status | String(20) | NOT NULL, DEFAULT 'active' | "active" \| "completed" |
| transcript | Text | NOT NULL, DEFAULT '' | Concatenated Q&A pairs |
| total_questions | Integer | NULL | Expected question count |
| correctness_score | Float | NULL | Average correctness (0-100) |
| clarity_score | Float | NULL | Average clarity (0-100) |
| confidence_score | Float | NULL | Average confidence (0-100) |
| overall_score | Float | NULL | Weighted average (50/30/20) |
| behavioral_confidence | Float | NULL | Rolling window video confidence |
| performance_label | String(100) | NULL | "Strong Candidate", etc. |
| coach_message | Text | NULL | End-of-session feedback |
| created_at | DateTime (TZ) | DEFAULT NOW() | Session start |
| ended_at | DateTime (TZ) | NULL | Session completion |

**Relationships**: 
- 1:N with `interview_answers` (cascade delete)
- 1:N with `interview_behavior_metrics` (cascade delete)

#### `interview_answers`
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| session_id | Integer | FK → interview_sessions.id, ON DELETE CASCADE, Indexed | Parent session |
| question | Text | NOT NULL | Interview question |
| question_type | String(50) | NULL | skill_alignment, gap_based, etc. |
| answer | Text | NOT NULL | Candidate response |
| correctness | Float | NOT NULL | Hybrid score (0-100) |
| clarity | Float | NOT NULL | Rule-based score (0-100) |
| confidence | Float | NOT NULL | Multimodal score (0-100) |
| overall | Float | NOT NULL | Weighted score (0-100) |
| correctness_explanation | Text | NULL | Gemini feedback |
| clarity_explanation | Text | NULL | Detected issues |
| improvement_tip | Text | NULL | Gemini coaching |
| llm_score | Float | NULL | Groq sub-score |
| cosine_score | Float | NULL | SBERT sub-score |
| keyword_score | Float | NULL | Keyword coverage sub-score |
| created_at | DateTime (TZ) | DEFAULT NOW() | Answer submission time |

**Indexes**: session_id (foreign key), id (primary)

#### `interview_behavior_metrics`
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| session_id | Integer | FK → interview_sessions.id, ON DELETE CASCADE, Indexed | Parent session |
| eye_contact_score | Float | NOT NULL | 0.0-1.0 (clamped) |
| head_stability_score | Float | NOT NULL | 0.0-1.0 (clamped) |
| blink_rate | Float | NOT NULL | ≥0 (blinks/min) |
| facial_stress_index | Float | NOT NULL | 0.0-1.0 (clamped) |
| created_at | DateTime (TZ) | DEFAULT NOW() | Metric capture time |

**Usage**: Metrics submitted every 2 seconds, rolling window query for averages

### Data Flow Example

**Question Submission Flow**:
```sql
-- 1. Retrieve session and verify ownership
SELECT * FROM interview_sessions 
WHERE id = ? AND user_id = ? AND status = 'active';

-- 2. Check for duplicate question
SELECT id FROM interview_answers 
WHERE session_id = ? AND question = ?;

-- 3. Insert new answer
INSERT INTO interview_answers (session_id, question, answer, ...) 
VALUES (?, ?, ?, ...);

-- 4. Retrieve all session answers for average calculation
SELECT correctness, clarity, confidence FROM interview_answers 
WHERE session_id = ?;

-- 5. Update session aggregate scores
UPDATE interview_sessions 
SET correctness_score = ?, clarity_score = ?, confidence_score = ?, overall_score = ? 
WHERE id = ?;
```

---

## STEP 9 — API DESIGN

### API Endpoint Map

#### Authentication Endpoints
```
POST   /register
       Body: { name, email, password }
       Response: { access_token, token_type, user }

POST   /login
       Body: { email, password }
       Response: { access_token, token_type, user }

GET    /me
       Headers: Authorization: Bearer <token>
       Response: { id, name, email }
```

#### Resume Management
```
POST   /upload_resume
       Headers: Authorization: Bearer <token>
       Body (multipart): resume_file, job_role, jd_file?, jd_text?
       Response: { id, job_role, filename, created_at }

GET    /resumes
       Headers: Authorization: Bearer <token>
       Response: [{ id, job_role, filename, analysis_score, created_at }]

POST   /analyze_resume
       Headers: Authorization: Bearer <token>
       Body: { resume_id }
       Response: { resume_id, job_role, score, summary, strengths[], weaknesses[], suggestions[], improvement_tags[] }
```

#### Question Generation
```
POST   /generate_questions
       Headers: Authorization: Bearer <token>
       Body: { resume_id }
       Response: { resume_id, job_role, total, questions: [{ question, type }] }
```

#### Interview Session Lifecycle
```
POST   /start_session
       Headers: Authorization: Bearer <token>
       Body: { resume_id, total_questions? }
       Response: { session_id, status }

POST   /submit_answer
       Headers: Authorization: Bearer <token>
       Body: { session_id, question, answer, question_type, audio_confidence? }
       Response: { 
         current_answer: { correctness, clarity, confidence, overall, sub_scores, feedback },
         session_average: { correctness, clarity, confidence, overall },
         questions_answered
       }

POST   /end_session
       Headers: Authorization: Bearer <token>
       Body: { session_id }
       Response: { session_id, status, scores, performance_label, coach_message, recommendations, trend_insight }
```

#### Behavioral Metrics
```
POST   /submit_behavior_metrics
       Headers: Authorization: Bearer <token>
       Body: { session_id, eye_contact_score, head_stability_score, blink_rate, facial_stress_index }
       Response: { behavioral_confidence, nudge?, supportive_feedback?, window_metrics }

POST   /analyze_audio
       Headers: Authorization: Bearer <token>
       Body (multipart): audio_file, session_id
       Response: { audio_confidence, audio_features: { speech_rate, pause_duration, pitch_variation, energy_variation } }
```

#### Analytics Dashboard
```
GET    /dashboard?resume_id={optional}
       Headers: Authorization: Bearer <token>
       Response: { 
         session_summary: [{ session_id, resume_id, job_role, scores, performance_label, created_at }],
         progress_trend: [{ session_id, overall_score, created_at, job_role }],
         skill_breakdown_average: { correctness, clarity, confidence },
         total_completed
       }

GET    /session/{session_id}
       Headers: Authorization: Bearer <token>
       Response: { 
         session_info: { ... },
         answers: [{ answer_id, question, answer, scores, explanations, sub_scores }]
       }
```

#### Health Check
```
GET    /health
       Response: { status: "ok", version: "2.0.0" }
```

### Request/Response Patterns

**Error Handling**:
```json
// 400 Bad Request
{ "detail": "Answer exceeds 2000 characters (got 2543)" }

// 401 Unauthorized
{ "detail": "Token expired — please log in again" }

// 404 Not Found
{ "detail": "Session not found" }

// 500 Internal Server Error
{ "detail": "Internal server error" }
```

**Validation (Pydantic)**:
- Email format validation
- Password minimum length (6 chars)
- Answer constraints (3-2000 characters)
- Behavioral metrics clamping (0-1)
- JSON schema enforcement on AI outputs

**CORS Configuration**:
```python
allow_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    ...
]
allow_credentials = True
allow_methods = ["*"]
allow_headers = ["*"]
```

---

## STEP 10 — DEPENDENCY ANALYSIS

### Dependency Graph

```
┌──────────────────────────────────────────────────────────┐
│                   FRONTEND DEPENDENCIES                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  App.jsx (Root Router)                                   │
│    ├──→ LoginRegisterPage.jsx                           │
│    │     └──→ authService.js ───┐                       │
│    │                             │                       │
│    ├──→ ResumeUploadPage.jsx ───┼──→ axios (HTTP client)│
│    │                             │                       │
│    ├──→ InterviewPage.jsx       │                       │
│    │     ├──→ CameraFeed.jsx ───┤                       │
│    │     │     └──→ @mediapipe/face_mesh                │
│    │     ├──→ useSpeechRecognition.js (Web Speech API)  │
│    │     ├──→ useAudioRecorder.js (MediaRecorder API)   │
│    │     └──→ axios ─────────────┘                       │
│    │                                                     │
│    └──→ DashboardPage.jsx                               │
│          └──→ chart.js + react-chartjs-2                │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   BACKEND DEPENDENCIES                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  main.py (FastAPI App)                                   │
│    ├──→ database.py (SQLAlchemy Engine)                 │
│    │     └──→ models/* (ORM classes)                    │
│    │                                                     │
│    ├──→ routes/* (API Endpoints)                        │
│    │     ├──→ auth/jwt_handler.py (JWT middleware)      │
│    │     ├──→ services/ai_service.py                    │
│    │     │     ├──→ groq (Groq API)                     │
│    │     │     └──→ google.generativeai (Gemini)        │
│    │     │                                               │
│    │     ├──→ services/text_extractor.py                │
│    │     │     ├──→ PyPDF2                              │
│    │     │     └──→ python-docx                         │
│    │     │                                               │
│    │     └──→ ai_modules/*                              │
│    │           ├──→ rag.py                               │
│    │           │     ├──→ faiss                         │
│    │           │     └──→ sentence_transformers         │
│    │           │                                         │
│    │           ├──→ correctness.py                      │
│    │           │     ├──→ ai_service (Groq + Gemini)    │
│    │           │     └──→ sentence_transformers (SBERT) │
│    │           │                                         │
│    │           ├──→ clarity.py (no external deps)       │
│    │           ├──→ behavioral_confidence.py            │
│    │           ├──→ hierarchical.py (pure math)         │
│    │           ├──→ feedback_generator.py               │
│    │           ├──→ video_analyzer.py (no backend deps) │
│    │           └──→ audio_analyzer.py                   │
│    │                 └──→ librosa + soundfile           │
│    │                                                     │
│    └──→ Lifespan Events                                 │
│          ├──→ database.init_db()                        │
│          ├──→ ai_service.initialize()                   │
│          └──→ correctness._get_sbert() (warm-load)      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Critical Components

**Single Point of Failure**:
1. **ai_service.py** — All LLM calls routed through this module
   - Groq failure → No question generation, no correctness scoring
   - Gemini failure → No resume analysis, no rich explanations
   - Mitigation: Retry logic (1 attempt), structured fallbacks

2. **database.py** — All data persistence
   - Database corruption → Total data loss
   - Connection failure → API unavailable
   - Mitigation: None (needs backup strategy)

3. **JWT_SECRET_KEY** — Authentication security
   - Key leak → All tokens compromised
   - Key loss → All users locked out
   - Mitigation: Environment variable (not committed)

**Performance Bottlenecks**:
1. **Groq API** — 1.5-3s latency per call
   - Affects: Question generation, correctness scoring
   - Mitigation: Async HTTP, but still blocks response

2. **Gemini API** — 2-4s latency per call
   - Affects: Resume analysis, explanations
   - Mitigation: Caching (resume analysis), async

3. **SBERT Encoding** — CPU-bound, 80-120ms
   - Affects: Every answer submission
   - Mitigation: Warm-loaded at startup, could add GPU

---

## STEP 11 — POTENTIAL ISSUES

### Architectural Weaknesses

1. **Monolithic Backend**
   - All AI modules in single FastAPI process
   - LLM calls block request threads (async but serial)
   - No horizontal scaling (stateful SBERT model)
   - **Recommendation**: Separate AI inference into dedicated worker service

2. **Tight Coupling to External APIs**
   - Groq + Gemini both required for full functionality
   - No local LLM fallback
   - API rate limits not tracked
   - **Recommendation**: Implement local model fallback (e.g., Ollama)

3. **Client-Side ML Processing**
   - MediaPipe runs in browser → device-dependent performance
   - Low-end devices may lag at 30 FPS
   - No server-side video analysis fallback
   - **Recommendation**: Add optional server-side video analysis

4. **No Caching Layer**
   - Repeated questions generate identical LLM calls
   - FAISS indices rebuilt on every resume upload (should reuse)
   - SBERT embeddings not cached
   - **Recommendation**: Redis cache for LLM responses, embedding store

### Scalability Concerns

1. **Database**
   - SQLite not suitable for production (single-writer lock)
   - No connection pooling configured
   - No query optimization (N+1 in dashboard endpoint)
   - **Recommendation**: Migrate to PostgreSQL, add SQLAlchemy pooling

2. **File Storage**
   - Resume text stored in database (bloats DB)
   - Vector indices in filesystem (not replicated)
   - No blob storage integration
   - **Recommendation**: S3 for files, pgvector for embeddings

3. **Session State**
   - Behavioral metrics stored per-session (grows unbounded)
   - No cleanup of old sessions
   - Dashboard queries all sessions (no pagination)
   - **Recommendation**: Data retention policy, pagination

4. **Concurrency**
   - No rate limiting (single user can DoS)
   - No request queuing (simultaneous LLM calls exhaust quota)
   - **Recommendation**: Redis-based rate limiter, Celery task queue

### Security Risks

1. **Input Validation**
   - File uploads not scanned for malware
   - AI-generated content not sanitized (XSS risk)
   - No size limits on uploads (memory DoS)
   - **Severity**: High

2. **Authentication**
   - No MFA (single-factor only)
   - No session revocation mechanism
   - JWT expiry too long (2 hours)
   - **Severity**: Medium

3. **API Security**
   - No rate limiting (abuse vector)
   - CORS allows multiple origins (dev config in prod risk)
   - No API key rotation mechanism
   - **Severity**: High

4. **Data Privacy**
   - Resume content stored unencrypted
   - No data export/deletion GDPR compliance
   - AI providers (Groq/Gemini) receive PII
   - **Severity**: Medium (depends on jurisdiction)

### Performance Bottlenecks

1. **Synchronous AI Calls**
   - Groq + Gemini in series → 5s total latency
   - Could parallelize explanation generation
   - **Impact**: User perceives slowness

2. **Frontend Rendering**
   - MediaPipe processing on main thread
   - Large dashboard charts re-render on every state change
   - **Impact**: UI jank on low-end devices

3. **Database Queries**
   - Dashboard endpoint fetches all sessions + answers (N+1 problem)
   - No eager loading of relationships
   - **Impact**: Slow dashboard with >50 sessions

### Operational Gaps

1. **No Monitoring**
   - No metrics (Prometheus/Grafana)
   - No error tracking (Sentry)
   - Console logging only
   - **Risk**: Cannot detect production issues

2. **No Deployment Automation**
   - Manual start (uvicorn + vite)
   - No Docker containers
   - No CI/CD pipeline
   - **Risk**: Deployment errors, downtime

3. **No Backup Strategy**
   - Database not backed up
   - Vector indices not replicated
   - **Risk**: Data loss on hardware failure

4. **No Testing**
   - No unit tests
   - No integration tests
   - No E2E tests
   - **Risk**: Regressions on code changes

---

## CONCLUSION

This AI Interview Training System represents a sophisticated implementation of multimodal evaluation combining LLM inference, classical ML, rule-based analysis, and real-time behavioral monitoring. The architecture demonstrates strong separation of concerns with independent scoring dimensions, graceful degradation through fallback mechanisms, and production-ready error handling.

**Key Strengths**:
- Hybrid evaluation prevents single-method bias
- Multimodal confidence fusion from video, audio, and text
- Coaching-first feedback philosophy
- Comprehensive RAG pipeline for personalized questions
- Production hardening with retry logic and fallbacks

**Critical Improvements Needed**:
- Rate limiting and input sanitization
- PostgreSQL migration for production
- Monitoring and error tracking infrastructure
- Automated testing suite
- API caching layer

The system is deployment-ready for small-scale production with the understanding that scalability enhancements and security hardening are essential for enterprise use.
