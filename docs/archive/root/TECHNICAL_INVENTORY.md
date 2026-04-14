# LetsTrain.ai – Complete Technical Inventory

**Project Name:** Multimodal AI Interview Training Platform  
**Current Status:** Phase 4 Complete - Core System Functional  
**Last Updated:** April 2026

---

## 📋 Table of Contents
1. [Backend Architecture](#backend-architecture)
2. [Frontend Architecture](#frontend-architecture)
3. [Features Implemented](#features-implemented)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Technology Stack](#technology-stack)
6. [Database Schema](#database-schema)

---

## Backend Architecture

### API Routes & Endpoints

#### **Authentication Routes** (`/backend/routes/auth_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/register` | POST | User registration with email/password | ❌ |
| `/login` | POST | User login, returns JWT token | ❌ |
| `/me` | GET | Get current authenticated user info | ✅ |

**Key Features:**
- Password hashing with bcrypt
- JWT token generation & validation
- Email validation (Pydantic EmailStr)

---

#### **Resume Routes** (`/backend/routes/resume_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/upload_resume` | POST | Upload resume + job description | ✅ |
| `/resumes` | GET | List all user's resumes | ✅ |
| `/analyze_resume` | POST | AI analysis of resume vs job description | ✅ |

**Supported File Formats:** PDF, DOCX, TXT  
**Resume Analysis Model:** Gemini 1.5 Flash  
**Analysis Output:** Score (0-100), strengths, weaknesses, suggestions, improvement tags

---

#### **Question Generation Routes** (`/backend/routes/question_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/generate_questions` | POST | Generate interview questions from resume | ✅ |

**Question Generation Pipeline:**
1. Resume + JD combined into context
2. Text chunked (chunk_size=300 words)
3. FAISS vector index created (if not exists)
4. Groq LLaMA 3.3 70B generates 3 question types:
   - **Skill alignment:** Match resume skills to job role
   - **Gap analysis:** Test weaker areas from job description
   - **Project depth:** Deep-dive into candidate's projects

---

#### **Session Routes** (`/backend/routes/session_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/start_session` | POST | Begin new interview session | ✅ |
| `/submit_answer` | POST | Submit answer (text or audio) | ✅ |
| `/session/{session_id}/next_question` | GET | Get next adaptive question | ✅ |
| `/end_session` | POST | Complete session & compute final scores | ✅ |
| `/session/{session_id}` | DELETE | Delete session | ✅ |
| `/analytics/summary` | GET | Session analytics/statistics | ✅ |

**Answer Submission Features:**
- Supports both typed and audio answers
- Audio file validation: max 5MB, max 60 seconds
- Whisper ASR for speech-to-text (base model)
- Audio transcription with timeout protection
- Fallback to typed answer if transcription fails

**Session Scoring:**
- **Correctness:** 50% - uses hybrid approach:
  - Groq LLaMA 3.3 70B: 60% weight (raw LLM evaluation)
  - SBERT cosine similarity: 25% weight (semantic relevance)
  - Keyword coverage: 15% weight (domain terms)
- **Clarity:** 30% - rule-based evaluation:
  - Length adequacy
  - Repetition analysis
  - Filler word detection
  - Sentence structure
- **Confidence:** 20% - multimodal fusion:
  - Video features (60%): eye contact, head stability, stress
  - Audio features (25%): speech rate, pauses, pitch/energy variation
  - Text hesitation (15%): filler words in transcription

---

#### **Behavioral Analysis Routes** (`/backend/routes/behavior_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/submit_behavior_metrics` | POST | Store video behavioral data each frame | ✅ |
| `/analyze_audio` | POST | Extract audio features (deprecated - inline) | ✅ |

**Video Features (from MediaPipe FaceMesh):**
- Eye contact score (0-1): Iris gaze deviation from center
- Head stability (0-1): Nose tip movement over 10-frame window
- Blink rate (blinks/min): Eye aspect ratio (EAR) tracking
- Facial stress index (0-1): Muscle tension indicators

**Audio Features (from librosa):**
- Speech rate (0-1 normalized): Word per minute
- Pause duration (0-1): Silence ratio in audio
- Pitch variation (0-1): F0 contour variance
- Energy variation (0-1): RMS energy fluctuation

---

#### **Dashboard Routes** (`/backend/routes/dashboard_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/dashboard` | GET | Get performance analytics dashboard | ✅ |
| `/session/{session_id}` | GET | Get detailed session results | ✅ |

**Dashboard Analytics:**
- Session summary: scores across all sessions
- Progress trend: overall_score over time
- Skill breakdown: average correctness, clarity, confidence
- Total completed sessions

---

#### **Feedback Routes** (`/backend/routes/feedback_routes.py`)
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/session/{session_id}/feedback` | GET | Get comprehensive session feedback | ✅ |

**Feedback Components:**
- Strengths (areas where candidate excelled)
- Weaknesses (areas needing improvement)
- Behavior observations (from detected issues)
- Final recommendation with actionable insights

---

### Backend AI Modules

#### **Text Evaluation Modules**

**`/backend/ai_modules/correctness.py`**
- **Hybrid Scoring (0-100):**
  - **Groq LLaMA 3.3 70B** (60% weight): Raw LLM evaluation
  - **SBERT all-MiniLM-L6-v2** (25% weight): Cosine similarity between Q&A
  - **Keyword Coverage** (15% weight): Important terms from question in answer
- **Fallback Values:**
  - Groq failure: 60.0 (neutral)
  - SBERT failure: 60.0 (neutral)
  - Keyword failure: 50.0 (neutral)
- **LLM-Generated Explanations:** Gemini 1.5 Flash produces correctness_explanation + improvement_tip
- **Safe API Calls:** All external calls wrapped in try/except with timeouts/retries

**`/backend/ai_modules/clarity.py`**
- **Scoring (0-100):**
  - Word count penalty (smooth curve, not cliff)
  - Repeated phrase detection (max 20 point deduction)
  - Filler word analysis (um, uh, like, basically, etc.)
  - Sentence structure validation
  - Incomplete sentence detection
- **Ideal Range:** 40-60 words per answer
- **Minimum:** 3 words (hard limit in validation)

**`/backend/ai_modules/hierarchical.py`**
- **Overall Score Formula:**
  ```
  overall = 0.50 * correctness + 0.30 * clarity + 0.20 * confidence
  ```
- **Weights Match Original Specification** (per project requirements)

**`/backend/ai_modules/behavioral_confidence.py`**
- **Video Confidence (0-100):**
  - Eye contact (40% weight): 0-1 normalized score
  - Head stability (30% weight): 0-1 normalized score
  - Blink rate (20% weight): Inverted (high blink = lower confidence)
  - Facial stress (10% weight): Inverted (high stress = lower confidence)
- **Audio Confidence (0-100):**
  - Speech rate (30% weight): 0-1 normalized
  - Pause duration (30% weight): 0-1 normalized
  - Pitch variation (25% weight): 0-1 normalized
  - Energy variation (15% weight): 0-1 normalized
- **Multimodal Fusion (0-100):**
  - Video (60% weight)
  - Audio (25% weight) - optional
  - Text hesitation (15% weight) - optional
  - **Critical:** Confidence never reduces correctness score

---

#### **Audio & Video Analysis Modules**

**`/backend/ai_modules/audio_analyzer.py`**
- Extracts prosodic features from audio bytes
- Uses librosa for signal processing
- Supports WAV, MP3, M4A, FLAC, OGG, WebM, AAC
- Returns normalized 0-1 scores for speech_rate, pause_duration, pitch_variation, energy_variation

**`/backend/ai_modules/audio_transcriber.py`**
- **Whisper "base" model** (OpenAI)
- Max file size: 5MB
- Max duration: 60 seconds (validated during transcription)
- Timeout: 25 seconds (prevents hanging)
- Safe temp file handling: UUID-based naming, automatic cleanup
- Transcription only updated if non-empty

**`/backend/ai_modules/video_analyzer.py`**
- Processes MediaPipe FaceMesh landmarks (468 points)
- **Computed Metrics:**
  - Eye contact: Iris position deviation from eye center (0-1)
  - Head stability: Nose tip movement over 10-frame window (0-1)
  - Blink detection: Eye Aspect Ratio (EAR) with threshold 0.22
  - Facial stress: Muscle tension indicators (0-1)

---

#### **RAG & Question Generation Module** (`/backend/ai_modules/rag.py`)

**Vector Store:**
- **Index Format:** FAISS (Flat L2)
- **Embedding Model:** SentenceTransformers all-MiniLM-L6-v2
- **Storage:** `/backend/vector_store/{resume_id}.index` + `.pkl`
- **Chunking:** 300-word chunks with overlap

**Question Generation Pipeline:**
1. Retrieve context from FAISS (top-5 chunks for query)
2. Inject into Groq LLaMA 3.3 70B
3. Generate 10-20 questions (configurable)
4. Classify by difficulty (1=easy, 2=medium, 3=hard)
5. Tag by type: skill_alignment, gap_based, project_based

**Adaptive Question Selection** (`/backend/services/adaptive_question_service.py`):
- Deterministic cold-start (first 3 questions)
- Near-duplicate detection (lexical_similarity > 0.88)
- Topic diversity tracking
- Difficulty trending based on performance
- Resume risk flagging (analysis_score < 60%)
- Reuse strategy: Mix new + previous questions

---

#### **Feedback Generation Module** (`/backend/ai_modules/feedback_generator.py`)

**Per-Answer Feedback:**
- Answer-level strengths/areas to improve
- Coaching tips (STAR method, foundational knowledge, etc.)
- Based on correctness/clarity/confidence scores

**Session Summary Feedback:**
- Overall performance label
- Strongest/weakest dimension
- Behavioral observations
- Trend analysis (improving/declining)
- Final recommendation with actionable steps

**Real-Time Supportive Nudges:**
- Triggered when stress/hesitation detected
- Examples: "Take a moment...", "You're doing well, continue calmly."

---

### Backend Database Models (SQLAlchemy)

#### **User Model** (`/backend/models/user.py`)
```
Columns:
  id (PK, autoincrement)
  name (String, required)
  email (String, unique, required)
  password_hash (String, required)
  is_active (Boolean, default=True)
  created_at (DateTime, auto-generated)
```

#### **Resume Model** (`/backend/models/resume.py`)
```
Columns:
  id (PK)
  user_id (FK → User, CASCADE)
  resume_text (Text, required)
  jd_text (Text, required)
  job_role (String, required)
  filename (String)
  
  AI Analysis Results (populated by /analyze_resume):
  analysis_score (Float, 0-100)
  analysis_model_used (String: 'gemini' | 'fallback')
  strengths (Text, JSON array)
  weaknesses (Text, JSON array)
  suggestions (Text, JSON array)
  improvement_tags (Text, JSON array)
  analysis_summary (Text)
  
  created_at (DateTime)
```

#### **InterviewSession Model** (`/backend/models/session.py`)
```
Columns:
  id (PK)
  user_id (FK → User, CASCADE)
  resume_id (FK → Resume, CASCADE)
  status (String: 'active' | 'completed')
  
  Interview State:
  transcript (Text, accumulated answers)
  total_questions (Integer)
  max_questions (Integer, default=10)
  current_difficulty (Integer, 1-3)
  
  Adaptive Interview Tracking:
  new_questions_count (Integer)
  reused_questions_count (Integer)
  last_question_was_reused (Boolean)
  resume_risk_flag (Boolean)
  last_difficulty_change_turn (Integer)
  
  Aggregate Scores (0-100):
  correctness_score (Float)
  clarity_score (Float)
  confidence_score (Float)
  overall_score (Float)
  behavioral_confidence (Float)
  
  Coach Feedback:
  performance_label (String)
  coach_message (Text)
  
  created_at (DateTime)
  ended_at (DateTime, when session completes)
  
  Relationships:
  answers → InterviewAnswer (1:many, cascade delete)
  behavior_metrics → InterviewBehaviorMetric (1:many, cascade delete)
  behavior_issues → BehaviorIssue (1:many, cascade delete)
```

#### **InterviewAnswer Model** (`/backend/models/answer.py`)
```
Columns:
  id (PK)
  session_id (FK, required)
  resume_id (FK, optional)
  
  Question:
  question (Text, required)
  normalized_question (Text, indexed)
  question_type (String: skill_alignment | gap_based | project_based)
  difficulty_level (Integer, 1-3)
  topic (String)
  
  Reuse Tracking:
  is_reused (Boolean, default=False)
  selection_reason (String)
  selection_context (Text, JSON)
  previous_score (Float, score from reused question's prior attempt)
  
  Candidate Response:
  answer (Text, required)
  transcription (Text, nullable - from Whisper if audio provided)
  
  Evaluation Scores (0-100):
  correctness (Float, required)
  clarity (Float, required)
  confidence (Float, required)
  overall (Float, required)
  
  Detailed Scoring Breakdown:
  llm_score (Float, from Groq)
  cosine_score (Float, from SBERT)
  keyword_score (Float, from keyword analysis)
  
  AI-Generated Explanations (stored for posterity):
  correctness_explanation (Text)
  clarity_explanation (Text)
  improvement_tip (Text)
  
  created_at (DateTime)
```

#### **InterviewBehaviorMetric Model** (`/backend/models/behavior_metric.py`)
```
Columns:
  id (PK)
  session_id (FK, required, indexed)
  
  Video Features (0-1 normalized):
  eye_contact_score (Float)
  head_stability_score (Float)
  blink_rate (Float, blinks per minute)
  facial_stress_index (Float)
  
  created_at (DateTime)
  
  Window-Based Aggregation:
  Rolling 5-second average computed over recent metrics
```

#### **BehaviorIssue Model** (`/backend/models/behavior_issue.py`)
```
Columns:
  id (PK)
  session_id (FK, required, indexed, CASCADE delete)
  question_index (Integer, 0-indexed)
  
  issue (Enum: 'face_not_present' | 'looking_away' | 'multiple_faces')
  severity (Enum: 'low' | 'medium' | 'high')
  
  created_at (DateTime)
```

---

### Backend Services

#### **AI Service** (`/backend/services/ai_service.py`)
- **Groq Client:**
  - Model: LLaMA 3.3 70B
  - Retry logic: 1 retry max on failure
  - Timeout: 20 seconds default
  - Fallback: Graceful degradation with fallback output
- **Gemini Client:**
  - Model: Gemini 1.5 Flash
  - Used for: Resume analysis, rich explanations
  - Timeout: 15 seconds

#### **Feedback Service** (`/backend/services/feedback_service.py`)
- Generates comprehensive session feedback
- Analyzes strengths/weaknesses from answer data
- Integrates behavioral issue observations
- Produces actionable recommendations

#### **Adaptive Question Service** (`/backend/services/adaptive_question_service.py`)
- Selects next question based on:
  - Performance trend (correctness scores)
  - Difficulty adjustment (scale up/down based on performance)
  - Topic diversity (avoid repetition)
  - Resume risk detection (lower difficulty if resume score < 60%)
  - Reuse strategy (balance new vs. previous questions)

#### **Text Extraction Service** (`/backend/services/text_extractor.py`)
- Extracts text from PDF (PyPDF2)
- Extracts text from DOCX (python-docx)
- Extracts text from TXT files
- Input validation and error handling

#### **Text Normalization Service** (`/backend/services/text_normalization.py`)
- Normalizes questions for near-duplicate detection
- Computes lexical similarity (includes spelling variations)
- Handles punctuation/capitalization normalization

---

## Frontend Architecture

### Pages & Components

#### **Main App Routing** (`/frontend/src/App.jsx`)
| Route | Component | Purpose |
|-------|-----------|---------|
| Login | LoginRegisterPage | User authentication |
| Dashboard | DashboardPage | Performance analytics & session history |
| Upload Resume | ResumeUploadPage | Resume + JD upload & analysis |
| Interview | InterviewPage | Live interview session |
| Feedback | FeedbackPage | Post-interview feedback & insights |

---

### Component Structure

#### **Authentication Module** (`/frontend/src/components/auth/`)
- `AuthHeader.jsx` - Top navigation with auth info
- `AuthToggle.jsx` - Login/Logout toggle
- `LoginForm.jsx` - Email/password login form
- `RegisterForm.jsx` - New user registration form
- `LoginRegisterPage.jsx` - Auth page wrapper

**Key Features:**
- JWT token storage in localStorage
- Error message extraction from backend responses
- Auto-redirect on auth failure

---

#### **Resume Upload Module** (`/frontend/src/components/ResumeUploadPage.jsx`)
**Features:**
- File upload: Resume (PDF/DOCX/TXT)
- File upload OR text: Job Description
- Job role text field
- Resume analysis display (score, strengths, weaknesses, suggestions)
- Re-analysis button with force_refresh flag

**Workflow:**
```
1. Upload resume file + enter job role
2. Optional: Upload JD file OR paste JD text
3. Click "Upload"
4. Backend extracts text, stores resume record
5. Auto-trigger analyze_resume
6. Display analysis results
```

---

#### **Interview Module** (`/frontend/src/components/InterviewPage.jsx`)
**Main Components:**
- `CameraFeed.jsx` - Webcam video capture + MediaPipe FaceMesh
- Question display
- Answer input (text or voice)
- Submit button

**Interview Workflow:**
```
1. SELECT: Resume from list
2. CLICK: "Start Interview"
3. backend/start_session with resume_id
4. For each question (up to max):
   a. Display question
   b. Capture video (MediaPipe landmarks every frame)
   c. Record audio (optional)
   d. User types/speaks answer
   e. Submit answer → /submit_answer
   f. Backend evaluates (correctness, clarity, confidence)
   g. Get next_question → /session/{id}/next_question
   h. Send behavior metrics → /submit_behavior_metrics
5. CLICK: "End Interview"
   → backend/end_session (aggregate scores)
   → Redirect to feedback page
```

---

#### **Dashboard Module** (`/frontend/src/components/DashboardPage.jsx`)
**Sub-components:**
- `ScoreCard.jsx` - Individual score display (correctness, clarity, confidence, overall)
- `StrengthsSection.jsx` - Strengths from latest session feedback
- `WeaknessesSection.jsx` - Weaknesses & improvement areas
- `BehaviorSection.jsx` - Behavioral observations (eye contact, blink rate, stress, etc.)
- `ChartsSection.jsx` - Performance trends over time (Chart.js)
- `StatsGrid.jsx` - Summary statistics (total sessions, avg scores)
- `RecommendationsSection.jsx` - Actionable next steps

**Features:**
- Resume filter dropdown
- Session history timeline
- Skill breakdown radar chart (correctness vs clarity vs confidence)
- Progress trend line chart

---

#### **Feedback Module** (`/frontend/src/components/feedback/`)
- `FeedbackPage.jsx` - Main feedback display (route: `/feedback`)
- `ScoreCard.jsx` - Detailed score breakdowns
- `StrengthsSection.jsx` - Strengths highlighting
- `WeaknessesSection.jsx` - Weaknesses + recommendations
- `BehaviorSection.jsx` - Behavioral analysis summary
- `ChartsSection.jsx` - Performance comparison charts
- `StatsGrid.jsx` - Session statistics
- `RecommendationsSection.jsx` - Personalized recommendations

---

### Frontend Utilities & Hooks

#### **Services** (`/frontend/src/services/`)

**`authService.js`**
```javascript
exports:
  - register({ name, email, password })
  - login({ email, password })
  - getMe(token)
  
Returns: { success, data/message }
Error handling: Extracts backend error.response.data.detail
```

**`sessionService.js`**
```javascript
exports:
  - deleteSession(sessionId)
  - getSession(sessionId)
  
Features:
  - Retryable error detection (409 = conflict, 5xx = server error)
  - Auto-extracts backend error messages
```

---

#### **Custom Hooks** (`/frontend/src/hooks/`)

**`useAnswerSubmit.js`**
```javascript
Functionality:
  - Submit typed or audio answer to /submit_answer
  - Handle multipart form data (answer + audio file)
  - Validate audio size constraints
  - Extract evaluation scores from response
  - Handle concurrent submission prevention
Options:
  - onSuccess(data) callback
  - onError(error) callback
```

---

#### **UI Components**

**`Toast.jsx`** - Notification system
- Info, success, error, warning message types
- Auto-dismiss after 4 seconds
- Stacked display

**`ConfirmDialog.jsx`** - Confirmation modal
- Yes/No confirmation
- Custom title/message
- Callback on confirm

**`CameraFeed.jsx`** - Webcam & MediaPipe Integration
- Webcam video stream (WebRTC)
- MediaPipe FaceMesh for facial landmarks
- Real-time feature extraction:
  - Eye contact ratio
  - Head stability
  - Blink detection
  - Facial stress indicators
- Frame-by-frame metric calculation
- 5-second rolling window averages
- Stress/hesitation nudges overlay

---

## Features Implemented

### ✅ Resume Processing
- **File Upload:** PDF, DOCX, TXT support
- **Text Extraction:** Automated parsing of resume & JD
- **AI Analysis:** Gemini 1.5 Flash evaluates resume vs job description
- **Output:** Score (0-100), strengths, weaknesses, suggestions, improvement tags
- **Caching:** Analysis cached (unless force_refresh requested)

### ✅ Question Generation
- **RAG Pipeline:** FAISS vector index from resume chunks
- **LLM:** Groq LLaMA 3.3 70B generates contextual questions
- **Types:** Skill alignment, gap analysis, project-depth
- **Difficulty:** 1-3 level classification
- **Adaptive Selection:** Mix of new questions + reused with performance-based difficulty

### ✅ Interview Flow
- **Session Management:** Create session → answer questions → end session
- **Status Tracking:** Active/completed states
- **Adaptive Progression:** Difficulty scales based on performance
- **Answer Types:** Text or speech (Whisper transcription)
- **Limit Control:** Configurable question count (default 10)

### ✅ Answer Evaluation
- **Correctness Scoring (0-100):**
  - Groq LLaMA 3.3 70B: 60% weight
  - SBERT cosine: 25% weight
  - Keyword coverage: 15% weight
- **Clarity Scoring (0-100):**
  - Word count (20-60 ideal)
  - Repetition detection
  - Filler word analysis
  - Sentence structure validation
- **Confidence Scoring (0-100):**
  - Multimodal fusion from video + audio + text
  - Eye contact + head stability + blink + stress (video)
  - Speech rate + pauses + pitch/energy (audio)
  - Text hesitation markers
- **Hierarchical Scoring:** Overall = 0.50*correct + 0.30*clarity + 0.20*confidence

### ✅ Audio Behavioral Analysis
- **Features Extracted:**
  - Speech rate (WPM-based)
  - Pause duration (silence ratio)
  - Pitch variation (F0 contour)
  - Energy variation (RMS fluctuation)
- **Library:** librosa + soundfile
- **Integration:** Contributes to confidence score only

### ✅ Video Behavioral Analysis
- **Features Extracted:**
  - Eye contact (iris gaze deviation)
  - Head stability (nose movement)
  - Blink rate (EAR-based detection)
  - Facial stress indicators
- **Library:** MediaPipe FaceMesh (468 landmarks)
- **Processing:** Frontend captures, sends landmarks to backend
- **Integration:** Contributes to confidence score only

### ✅ Feedback Generation
- **Per-Answer Feedback:**
  - Strengths & areas to improve
  - Coaching tips (STAR method, foundational knowledge, etc.)
- **Session Feedback:**
  - Overall performance label
  - Strongest/weakest dimension
  - Behavioral observations
  - Actionable recommendations
- **Real-Time Supportive Nudges:**
  - Triggered on detected stress/hesitation
  - Encouraging, non-judgmental tone

### ✅ Dashboard & Analytics
- **Session Summary:** All completed interviews listed
- **Performance Trends:** Score progression over time
- **Skill Breakdown:** Average correctness, clarity, confidence
- **Progress Charts:** Line charts (trends), radar charts (skill profile)
- **Resume Filter:** View analytics for specific resume

### ✅ Session Tracking
- **Database Storage:** All answers, scores, feedback stored in SQLite
- **Session State:** Active/completed status
- **Transcript:** Cumulative answer history
- **Metadata:** Question count, difficulty progression, risk flags

---

## Data Flow Diagrams

### 🔄 Resume Upload & Analysis Flow
```
Frontend (ResumeUploadPage)
    ↓ uploads resume file + job_role + JD
Backend (/upload_resume)
    ↓ extract text (PyPDF2/python-docx)
    ↓ validate text not empty
Database (INSERT Resume record)
    ↓ resume_id generated
Frontend (auto-trigger)
Backend (/analyze_resume)
    ↓ Gemini 1.5 Flash (prompt with resume + JD)
    ↓ Parse JSON response: score, strengths, weaknesses, suggestions
Database (UPDATE Resume with analysis results)
    ↓ cache results
Frontend (display analysis on page)
```

### 🔄 Question Generation Flow
```
Frontend (InterviewPage)
    ↓ CLICK "Generate Questions"
Backend (/generate_questions with resume_id)
    ↓ Fetch resume (combine resume_text + jd_text)
    ↓ chunk_text(combined, chunk_size=300)
    ↓ _get_embedding_model() [SBERT all-MiniLM-L6-v2]
    ↓ index_exists(resume_id) → if not, create FAISS index
Database (vector_store/{resume_id}.index + .pkl)
    ↓ generate_questions() via Groq + RAG
    ↓ For each question type (skill_alignment, gap_based, project_based):
    ↓   - retrieve_context(resume_id, query, top_k=5)
    ↓   - Groq prompt with retrieved chunks
    ↓   - Parse difficulty + type + topic
Frontend (display 10+ questions with difficulty levels)
```

### 🔄 Interview Session Flow
```
Frontend (InterviewPage)
    ↓ User selects resume + clicks "Start Interview"
Backend (/start_session with resume_id)
    ↓ Create InterviewSession record (status='active')
    ↓ choose_next_question() → first adaptive question
Database (INSERT InterviewSession)
Frontend (display first question)
    ↓ User answers (text or audio)
    ↓ Frontend captures video frames (MediaPipe FaceMesh)
    ↓ Frontend calculates behavior metrics (eye_contact, head_stability, blink, stress)
    ↓ User clicks "Submit Answer"
Backend (/submit_answer)
    ↓ If audio provided:
    ↓   - Validate file size/duration
    ↓   - Transcribe with Whisper (base model)
    ↓   - Use transcription as answer text
    ↓ evaluate_correctness(question, answer) → (score, llm_score, cosine_score, keyword_score)
    ↓ evaluate_clarity(question, answer) → (score, explanation)
    ↓ compute_multimodal_confidence(video_scores, audio_scores, text_hesitation)
    ↓ Compute overall = 0.50*correctness + 0.30*clarity + 0.20*confidence
    ↓ Store InterviewAnswer record with all scores
    ↓ choose_next_question() → adaptive selection
Database (INSERT InterviewAnswer, UPDATE InterviewSession.transcript)
Frontend (/submit_behavior_metrics)
    ↓ Send video metrics (eye_contact, head_stability, blink_rate, facial_stress)
Backend (/submit_behavior_metrics)
    ↓ Store InterviewBehaviorMetric
    ↓ Check for behavior issues (face_not_present, looking_away, multiple_faces)
    ↓ If issue detected, INSERT BehaviorIssue record
Database (INSERT InterviewBehaviorMetric, possibly BehaviorIssue)
Frontend (get next question → repeat until max questions or early stop)
    ↓ User clicks "End Interview"
Backend (/end_session)
    ↓ Aggregate scores across all answers
    ↓ correctness_score = AVG(correctness_scores)
    ↓ clarity_score = AVG(clarity_scores)
    ↓ confidence_score = AVG(confidence_scores)
    ↓ overall_score = compute_overall()
    ↓ performance_label = label(overall_score)
    ↓ coach_message = coaching_feedback()
    ↓ Update InterviewSession: status='completed', ended_at=now()
Database (UPDATE InterviewSession with final scores)
Frontend (/session/{session_id}/feedback)
    ↓ Fetch session, answers, behavior_issues
    ↓ generate_feedback_report(session_id, db)
    ↓ Identify strengths/weaknesses from scores
    ↓ Behavioral observations from BehaviorIssue records
Frontend (display FeedbackPage with detailed insights)
```

### 🔄 Dashboard Analytics Flow
```
Frontend (DashboardPage)
    ↓ Load with optional resume_id filter
Backend (/dashboard?resume_id={resume_id if selected})
    ↓ If resume_id not provided, fetch latest resume for user
    ↓ Query InterviewSession (status='completed', user_id=current_user)
    ↓ If resume_id, filter by resume_id
    ↓ Load eager relationships: answers, behavior_metrics, behavior_issues
    ↓ Build response:
    ↓   - session_summary: [{ session_id, overall_score, correctness/clarity/confidence, created_at }, ...]
    ↓   - progress_trend: [{ session_id, overall_score, created_at }, ...]
    ↓   - skill_breakdown_average: { correctness_avg, clarity_avg, confidence_avg }
    ↓   - total_completed: int
Frontend (render charts)
    ↓ Line chart (overall_score trend over time)
    ↓ Radar chart (correctness vs clarity vs confidence skill profile)
    ↓ Session summary cards (individual session details)
```

---

## Technology Stack

### Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| **Framework** | FastAPI | ≥0.109.0 |
| **Server** | Uvicorn | ≥0.27.0 |
| **Database** | SQLite or PostgreSQL | Latest |
| **ORM** | SQLAlchemy | ≥2.0.0 |
| **Auth** | PyJWT + bcrypt | ≥2.8.0, ≥4.1.0 |
| **Validation** | Pydantic | ≥2.0.0 |
| **File Parsing** | PyPDF2, python-docx | ≥3.0.0, ≥1.1.0 |
| **AI - Scoring** | Groq (LLaMA 3.3 70B) | Latest |
| **AI - Analysis** | Gemini 1.5 Flash | Latest |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) | ≥2.2.0 |
| **Vector DB** | FAISS | ≥1.7.4 |
| **Audio** | librosa, soundfile | ≥0.10.0, ≥0.12.0 |
| **ML** | scikit-learn, numpy | ≥1.3.0, ≥1.24.0 |
| **HTTP** | requests | ≥2.31.0 |

### Frontend
| Layer | Technology | Version |
|-------|-----------|---------|
| **Framework** | React | Latest |
| **Build Tool** | Vite | Latest |
| **HTTP Client** | Axios | Latest |
| **UI Components** | Lucide Icons | Latest |
| **Styling** | Tailwind CSS | Latest |
| **Charts** | Chart.js | Latest |
| **ML** | MediaPipe (JS) | Latest |
| **Speech** | Web Speech API | Browser native |
| **Audio** | WebRTC MediaRecorder | Browser native |

---

## Environment Variables

### Backend (`.env`)
```
DATABASE_URL=sqlite:///./interview_prep.db
GROQ_API_KEY=<your-groq-key>
GEMINI_API_KEY=<your-gemini-key>
FRONTEND_URL=http://localhost:5173
```

### Frontend (`.env`)
```
VITE_API_URL=http://localhost:8000
```

---

## Running the System

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

### Accessing the System
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger UI)

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **API Endpoints** | 20+ |
| **Database Tables** | 6 |
| **AI Modules** | 9 |
| **Frontend Pages** | 5 |
| **Frontend Components** | 15+ |
| **AI Models Used** | 4 (Groq, Gemini, SBERT, Whisper) |
| **Supported File Formats** | 5 (PDF, DOCX, TXT, WAV, MP3, etc.) |

---

## Key Architectural Decisions

1. **Three-Dimensional Evaluation:** Correctness, Clarity, Confidence kept strictly independent
2. **Hybrid Correctness Scoring:** Combines LLM, semantic similarity, and keyword coverage for robustness
3. **Confidence ≠ Correctness:** Behavioral confidence never reduces technical correctness scores
4. **RAG with FAISS:** Vector store indexed per-resume for efficient retrieval
5. **Adaptive Questioning:** Deterministic selection strategy to balance difficulty & diversity
6. **Frontend Video Processing:** MediaPipe runs locally for privacy; only metrics sent to backend
7. **Whisper Transcription:** Local model for speech-to-text; no external audio storage
8. **Multimodal Fusion:** Weighted combination of video + audio + text signals for confidence

---

**Document Version:** 1.0  
**Last Updated:** April 2026  
**Author:** Faiza (FYP Implementation)
