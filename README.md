# 🎯 AI Interview Training System

A multimodal AI-powered coaching platform that evaluates interview performance across three independent dimensions: **Correctness**, **Clarity**, and **Confidence**. This system acts as an intelligent coach rather than a simple evaluator, providing adaptive feedback and tracking improvement over multiple sessions.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Core Features](#core-features)
- [Evaluation Methodology](#evaluation-methodology)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [System Workflow](#system-workflow)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## 🎓 Project Overview

The AI Interview Training System is designed to help candidates prepare for technical interviews using an intelligent coaching approach. Unlike traditional evaluators, this system:

✅ Evaluates using **three decoupled dimensions** (not conflating poor confidence with bad answers)  
✅ Provides **supportive, non-judgmental feedback**  
✅ Tracks **progress across multiple sessions**  
✅ Uses **multimodal analysis** (text, audio, video)  
✅ Generates **adaptive questions** based on resume and job description  
✅ Offers **real-time encouragement** when hesitation is detected  

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │ Webcam       │  │ Microphone  │  │ Speech Recognition   │   │
│  │ Capture      │  │ Capture     │  │ (Web Speech API)     │   │
│  └──────┬───────┘  └──────┬──────┘  └──────────────────────┘   │
│         │                 │                                      │
│         └─────────────────┼──────────────────────────────────┐   │
│                           │                                  │   │
│            ┌──────────────▼────────────────┐                 │   │
│            │   Interview UI Component     │                 │   │
│            │  - Question Display          │                 │   │
│            │  - Real-time Feedback        │                 │   │
│            │  - Score Visualization       │                 │   │
│            └──────────────────────────────┘                 │   │
└────────────────────────────┬─────────────────────────────────┘   │
                             │ HTTP/WebSocket                      │
        ┌────────────────────▼─────────────────────────┐            │
        │                                              │            │
┌───────▼──────────────────────────────────────────────▼────────────┐
│                     BACKEND (FastAPI)                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    API Routes Layer                         │ │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ │ │
│  │  │  Auth       │ │  Resume      │ │Questions │ │Sessions  │ │ │
│  │  │  Routes     │ │  Routes      │ │ Routes   │ │ Routes   │ │ │
│  │  └─────────────┘ └──────────────┘ └──────────┘ └──────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   AI Modules Layer                          │ │
│  │  ┌──────────────┐ ┌──────────┐ ┌─────────────┐ ┌─────────┐ │ │
│  │  │  Resume      │ │  Audio   │ │  Video      │ │  Text   │ │ │
│  │  │  Analyzer    │ │ Analyzer │ │  Analyzer   │ │Evaluator│ │ │
│  │  └──────────────┘ └──────────┘ └─────────────┘ └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Multimodal Fusion Engine                     │ │
│  │  Confidence Fusion + Clarity Analysis + Feedback Generator │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Services Layer                                 │ │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌────────────┐   │
│  │  │  RAG Pipeline    │ │ Adaptive Question│ │  Database  │   │
│  │  │  (FAISS + LLM)   │ │  Service         │ │  Service   │   │
│  │  └──────────────────┘ └──────────────────┘ └────────────┘   │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬────────────────────────────────────────┘
                            │ SQLAlchemy ORM
        ┌───────────────────▼──────────────────┐
        │      SQLite Database                 │
        │  - Users & Sessions                  │
        │  - Resume Data & Analysis            │
        │  - Question Bank                     │
        │  - Performance Scores                │
        │  - Feedback History                  │
        └──────────────────────────────────────┘
```

---

## ✨ Core Features

### 1. **Resume & Job Description Processing**
- Accepts PDF, DOC, or plain text uploads
- Extracts and cleans text content
- Generates semantic embeddings using SentenceTransformers
- Stores embeddings in FAISS vector database
- Chunks content for efficient retrieval

### 2. **Resume-Driven Question Generation (RAG)**
- Retrieves relevant resume/JD chunks via semantic similarity
- Uses Groq API for fast LLM question generation
- Generates 3 types of questions:
  - **Skill alignment** questions
  - **Gap analysis** questions
  - **Project-depth** questions
- Supports difficulty levels (1-5)

### 3. **Conversational AI Interviewer**
- Sequential question delivery
- Maintains interview session state
- Provides conversational pacing
- Optional TTS for question delivery

### 4. **Speech-to-Text Processing**
- Browser-based speech capture (Web Speech API)
- Real-time transcription of candidate responses
- Fallback to manual text input

### 5. **Audio Behavioral Analysis**
- Extracts prosodic features:
  - Speech rate (words per minute)
  - Pause duration (hesitation indicators)
  - Pitch variation (confidence markers)
  - Energy variation (engagement level)
- Uses **librosa** for audio processing
- Contributes **only to confidence estimation**

### 6. **Video Behavioral Analysis**
- Real-time webcam processing via **MediaPipe FaceMesh**
- Extracts features:
  - Eye contact ratio (direct gaze time)
  - Blink rate (stress indicator)
  - Head stability (composure)
  - Facial stress indicators (micro-expressions)
  - Gaze direction tracking
- Uses MediaPipe for efficient face tracking
- Contributes **only to confidence estimation**

### 7. **Text Answer Evaluation**
- LLM-based structured evaluation
- Produces:
  - **Correctness score** (0-100) - Knowledge accuracy
  - **Covered concepts** - Key topics addressed
  - **Missing points** - Important omissions
  - **Incorrect statements** - Factual errors
  - **Qualitative feedback** - Explanation quality

### 8. **Clarity Analysis**
- Evaluates explanation quality:
  - Logical flow of ideas
  - Explanation structure
  - Redundancy detection
  - Sentence completeness
- Independent of correctness and confidence
- Produces clarity score (0-100)

### 9. **Multimodal Confidence Fusion**
Combines multiple modalities:
- **Audio signals**: Speech rate, pitch, energy
- **Video signals**: Eye contact, blink rate, head stability
- **Text signals**: Hesitation markers, filler words, sentence completion
- Weighted fusion for final confidence score (0-100)

### 10. **Real-Time Supportive Feedback**
When hesitation/stress detected:
- "Take a moment and explain step by step."
- "You're doing well, continue calmly."
- "Breathe and organize your thoughts."
- Non-judgmental, encouraging tone

### 11. **Progress Tracking & Analytics**
Tracks:
- Session scores across time
- Correctness improvement trend
- Clarity improvement trend
- Confidence improvement trend

Dashboard displays:
- Performance radar charts
- Score trends over time
- Skills improvement insights
- Weak area recommendations

---

## 📊 Evaluation Methodology

### The Three Independent Dimensions

#### **1. Correctness (50% weight)**
Measures **knowledge accuracy and completeness**.

**Evaluation Process:**
- LLM analyzes answer against expected knowledge base
- Scores on:
  - LLM semantic matching (60%)
  - Keyword coverage (40%)
- Range: 0-100
- Independent of delivery style or confidence

**Example:**
```
Question: "Explain the difference between REST and GraphQL?"

Answer: "REST uses endpoints, GraphQL uses queries."

Evaluation:
- Correctness: 60/100 (mentions endpoints vs queries, but missing depth on:
  - Overfetching/underfetching concepts
  - Flexibility advantages
  - Performance implications)
- Clarity: 80/100 (concise, but could elaborate)
- Confidence: 85/100 (steady voice, good eye contact)

FINAL SCORE = (60 × 0.5) + (80 × 0.3) + (85 × 0.2) = 73/100
```

⚠️ **Critical Rule:** Low confidence CANNOT reduce correctness score.
- A nervous but knowledgeable candidate still gets high correctness
- Correctness is purely about what you know, not how you deliver it

#### **2. Clarity (30% weight)**
Measures **quality of explanation and communication**.

**Evaluation Process:**
- Analyzes explanation structure:
  - Logical progression of ideas
  - Sentence clarity and completeness
  - Redundancy and verbosity
  - Technical precision
- Range: 0-100
- Independent of correctness and confidence

**Example:**
```
Answer: "Um, well, so like, REST uses, uh, endpoints and HTTP methods,
         and then GraphQL, it's like, you query for specific data..."

Evaluated Clarity: 45/100
- Lacks structure (verbal filler: "um", "like", "uh")
- Incomplete sentences
- No logical progression
- Imprecise language

Same answer with better clarity:
"REST uses fixed endpoints and HTTP methods. GraphQL uses a single endpoint
with flexible queries. This means REST requires multiple calls for related data,
while GraphQL retrieves exactly what you need in one request."

Evaluated Clarity: 88/100
- Structured comparison
- Complete sentences
- Logical progression
- Technical precision
```

#### **3. Confidence (20% weight)**
Measures **behavioral delivery and composure**.

**Evaluation Process:**
- **Audio signals** (30% of confidence):
  - Speech rate: 120-150 WPM is optimal
  - Pause duration: < 2 seconds is ideal
  - Pitch variation: Moderate is better than monotone
  - Energy: Consistent throughout

- **Video signals** (50% of confidence):
  - Eye contact: >60% direct gaze = confident
  - Blink rate: Normal = 17 blinks/min; >25 = nervous
  - Head stability: Minimal head movement = composed
  - Facial expression: Relaxed features

- **Text signals** (20% of confidence):
  - Filler words: Low = confident
  - Sentence completion: High = confident
  - Hesitation markers: Low = confident

**Example:**
```
Audio Analysis:
- Speech rate: 135 WPM ✅ (optimal range)
- Pause duration: 1.2 seconds ✅ (thinking, not hesitation)
- Score: 82/100

Video Analysis:
- Eye contact: 72% ✅ (above 60%)
- Blink rate: 19 blinks/min ✅ (normal)
- Head stability: Minimal movement ✅
- Score: 88/100

Text Analysis:
- Filler words: 2 ("um", "like")
- Sentence completion: 95% ✅
- Score: 85/100

Confidence = (82×0.3) + (88×0.5) + (85×0.2) = 85/100
```

### Final Scoring Formula

```
Final Score = (Correctness × 0.50) + (Clarity × 0.30) + (Confidence × 0.20)

Range: 0-100

Interpretation:
- 85-100: Excellent (Strong knowledge, clear delivery, confident)
- 70-84: Good (Solid knowledge, good clarity, adequate confidence)
- 55-69: Fair (Some knowledge gaps, unclear delivery, needs confidence)
- 40-54: Poor (Significant gaps, poor clarity, low confidence)
- 0-39: Very Poor (Major knowledge deficiency)
```

---

## 🛠️ Technology Stack

### Frontend
- **React 18** - UI components and state management
- **Vite** - Lightning-fast build tool
- **TailwindCSS** - Styling framework
- **MediaPipe** - Real-time face/pose detection
- **Web Speech API** - Browser speech recognition
- **Chart.js** - Data visualization
- **Axios** - HTTP client

### Backend
- **FastAPI** - High-performance web framework
- **Python 3.10+** - Core language
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Local database (PostgreSQL for production)
- **JWT** - Authentication tokens

### AI & ML
- **Groq API** - Fast LLM for question generation
- **Google Gemini API** - Resume analysis
- **SentenceTransformers** - Semantic embeddings (SBERT)
- **FAISS** - Vector database for similarity search
- **librosa** - Audio feature extraction
- **MediaPipe** - Computer vision for video analysis
- **Whisper** - Speech-to-text (optional, uses Web Speech API currently)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 16+
- npm or yarn
- API Keys: Groq and Google Gemini (free)

### 1. Clone Repository
```bash
git clone https://github.com/Faiz1310/AI-Interview-Training-System.git
cd AI-Interview-Training-System
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env

# Edit .env with your API keys
# GROQ_API_KEY: Get from https://console.groq.com/keys
# GEMINI_API_KEY: Get from https://aistudio.google.com
```

### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Frontend .env should have:
# VITE_API_URL=http://localhost:8000
```

### 4. Run Backend

```bash
cd backend

# Option 1: Direct start
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Option 2: Using start script (Windows)
..\start.bat

# Option 3: With reload (development)
python -m uvicorn main:app --reload --port 8000
```

**Backend ready when you see:**
```
Application startup complete
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 5. Run Frontend

```bash
cd frontend

npm run dev
```

**Frontend ready at:** `http://localhost:5173`

### 6. First Time Setup
1. Navigate to `http://localhost:5173`
2. Register account
3. Login
4. Upload resume (PDF/DOC/TXT)
5. Upload job description
6. System generates interview questions
7. Start interview practice

---

## 🔄 System Workflow

### Complete Interview Session Flow

```
┌─────────────────────────────────────────────────────────┐
│            USER REGISTRATION & LOGIN                    │
│  Email + Password Authentication                        │
│  JWT Token Generation for Session Management            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         DOCUMENT UPLOAD & PROCESSING                    │
│                                                         │
│  Resume Upload                                          │
│  ├─ PDF/DOC/TXT parsing                               │
│  └─ Text extraction & cleaning                         │
│                                                         │
│  Job Description Upload                                 │
│  ├─ Content extraction                                 │
│  └─ Requirement parsing                                │
│                                                         │
│  Semantic Analysis                                      │
│  ├─ Generate embeddings (SBERT)                       │
│  ├─ Store in FAISS vector DB                          │
│  └─ Chunk for efficient retrieval                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│      ADAPTIVE QUESTION GENERATION (RAG)                 │
│                                                         │
│  Resume Chunking                                        │
│  ├─ Split into semantic chunks                        │
│  └─ Compute chunk embeddings                          │
│                                                         │
│  Relevance Matching                                     │
│  ├─ Similarity search: resume ↔ JD                    │
│  ├─ Identify gaps & strengths                         │
│  └─ Tag question types (skill/gap/depth)              │
│                                                         │
│  LLM Question Generation (Groq API)                    │
│  ├─ Generate 10-20 relevant questions                │
│  ├─ Vary difficulty levels                           │
│  └─ Store in question bank                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            INTERVIEW SESSION START                       │
│                                                         │
│  Initialize Session                                     │
│  ├─ Create InterviewSession record                    │
│  ├─ Link to resume                                    │
│  └─ Set total questions (typically 10)                │
│                                                         │
│  Setup Capture Devices                                  │
│  ├─ Request webcam permission                         │
│  ├─ Request microphone permission                     │
│  └─ Start video/audio stream                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         ADAPTIVE QUESTION SELECTION                      │
│                                                         │
│  Next Question Logic                                    │
│  ├─ Check previous answer difficulty                  │
│  ├─ If correct: increase difficulty                   │
│  ├─ If incorrect: maintain difficulty                 │
│  └─ Avoid repeating topics                           │
│                                                         │
│  Display Question                                       │
│  ├─ Show on screen                                    │
│  ├─ Optional: TTS delivery                            │
│  └─ Candidate record answer                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          REAL-TIME MULTIMODAL CAPTURE                    │
│                                                         │
│  Video Capture (MediaPipe)                              │
│  ├─ Face detection every 100ms                        │
│  ├─ Extract: eye contact, blink rate, head stability │
│  ├─ Track facial expressions                          │
│  └─ Store frame-level behavioral data                │
│                                                         │
│  Audio Capture (Web Audio API)                          │
│  ├─ Stream processing                                 │
│  ├─ Extract: speech rate, pause duration             │
│  ├─ Store audio file for analysis                     │
│  └─ Real-time transcription                          │
│                                                         │
│  Speech Recognition (Web Speech API)                    │
│  ├─ Convert speech to text in real-time              │
│  ├─ Display live transcription                        │
│  └─ Store transcript for evaluation                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│        ANSWER SUBMISSION & PROCESSING                    │
│                                                         │
│  When candidate finishes:                               │
│  ├─ Stop recording                                    │
│  ├─ Send transcript & media to backend               │
│  └─ Display "Evaluating..." message                   │
│                                                         │
│  Backend Processing:                                    │
│  ├─ Extract audio features (librosa)                 │
│  ├─ Extract video features aggregate                 │
│  └─ Store multimodal data with answer                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│        MULTIMODAL EVALUATION ENGINE                      │
│                                                         │
│  ┌─ Text Evaluation (LLM)                              │
│  │  ├─ Correctness: Knowledge accuracy (50%)         │
│  │  │  └─ LLM semantic matching (60%)                │
│  │  │  └─ Keyword coverage (40%)                     │
│  │  ├─ Clarity: Explanation quality (30%)            │
│  │  │  └─ Logical flow                               │
│  │  │  └─ Structure & completeness                   │
│  │  └─ Result: TextScores object                     │
│  │                                                   │
│  ├─ Audio Behavioral Analysis (librosa)              │
│  │  ├─ Speech rate (WPM)                            │
│  │  ├─ Pause duration (hesitation)                  │
│  │  ├─ Pitch variation (confidence)                 │
│  │  ├─ Energy variation (engagement)                │
│  │  └─ Result: AudioScores object                   │
│  │                                                   │
│  ├─ Video Behavioral Analysis (MediaPipe)            │
│  │  ├─ Eye contact ratio (gaze direction)           │
│  │  ├─ Blink rate (stress indicator)                │
│  │  ├─ Head stability (composure)                   │
│  │  ├─ Facial stress (micro-expressions)            │
│  │  └─ Result: VideoScores object                   │
│  │                                                   │
│  └─ Multimodal Fusion (Weighted Combination)        │
│     ├─ Confidence Score (20% weight)                │
│     │  = (AudioScores × 0.3)                        │
│     │  + (VideoScores × 0.5)                        │
│     │  + (TextHesitation × 0.2)                     │
│     │                                                │
│     └─ Final Score Calculation                      │
│        = (Correctness × 0.50)                       │
│        + (Clarity × 0.30)                           │
│        + (Confidence × 0.20)                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│     ADAPTIVE FEEDBACK & REINFORCEMENT                    │
│                                                         │
│  Detect Performance Issues                              │
│  ├─ Low confidence? → "You're doing great!"           │
│  ├─ Hesitation detected? → "Take your time..."        │
│  └─ Fast speech? → "Speak clearly and deliberately"  │
│                                                         │
│  Generate Coaching Feedback                             │
│  ├─ Strengths (2-3 key positive points)              │
│  ├─ Areas to improve (2-3 focus areas)                │
│  ├─ Specific tips for next time                       │
│  └─ Concept explanations for missed topics            │
│                                                         │
│  Display Results                                        │
│  ├─ Score breakdown (Correctness, Clarity, Conf.)    │
│  ├─ Visual feedback (emoji, colors)                   │
│  ├─ Detailed analysis (expandable)                    │
│  └─ Navigation: Next question or submit session      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│        SESSION COMPLETION & RECORDING                    │
│                                                         │
│  Data Persistence                                       │
│  ├─ Save all scores to database                       │
│  ├─ Store behavioral data & features                  │
│  ├─ Record feedback & recommendations                 │
│  └─ Calculate session aggregate score                 │
│                                                         │
│  Analytics Update                                       │
│  ├─ Update user performance trends                    │
│  ├─ Track skill improvement over sessions             │
│  ├─ Calculate progress percentage                     │
│  └─ Identify weak areas for targeted practice        │
│                                                         │
│  Dashboard Refresh                                      │
│  ├─ Update performance charts                         │
│  ├─ Show score history                               │
│  ├─ Display improvement recommendations               │
│  └─ Suggest follow-up practice areas                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🔌 API Documentation

### Authentication Endpoints

#### Register
```
POST /register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}

Response:
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "message": "User registered successfully"
}
```

#### Login
```
POST /login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### Resume Management

#### Upload Resume & JD
```
POST /upload_resume
Authorization: Bearer {token}
Content-Type: multipart/form-data

Files:
- resume_file: (PDF/DOC/TXT)
- jd_file: (PDF/DOC/TXT)

Form Data:
- job_role: "Senior Backend Engineer"

Response:
{
  "id": 42,
  "user_id": 1,
  "job_role": "Senior Backend Engineer",
  "analysis_score": 85.5,
  "resume_text": "John Doe...",
  "jd_text": "Looking for...",
  "created_at": "2026-04-15T10:30:00"
}
```

### Interview Session

#### Start Interview Session
```
POST /start_session
Authorization: Bearer {token}
Content-Type: application/json

{
  "resume_id": 42,
  "total_questions": 10
}

Response:
{
  "session_id": 1,
  "resume_id": 42,
  "total_questions": 10,
  "current_question_index": 0,
  "status": "in_progress",
  "created_at": "2026-04-15T10:35:00"
}
```

#### Get Next Question
```
GET /session/{session_id}/next_question
Authorization: Bearer {token}

Response:
{
  "question_id": 1,
  "question_text": "Explain the difference between REST and GraphQL",
  "question_index": 1,
  "total_questions": 10,
  "difficulty_level": 2,
  "category": "architecture"
}
```

#### Submit Answer
```
POST /session/{session_id}/submit_answer
Authorization: Bearer {token}
Content-Type: multipart/form-data

Files:
- audio_file: (WAV/MP3)
- video_file: (MP4/WebM)

Form Data:
- question_id: 1
- answer_text: "REST uses fixed endpoints..."
- speech_rate: 135
- pause_duration: 1.2
- audio_volume: 65

Response:
{
  "answer_id": 1,
  "scores": {
    "correctness": 82,
    "clarity": 88,
    "confidence": 85,
    "final_score": 85
  },
  "feedback": {
    "strengths": ["Good explanation", "Clear structure"],
    "areas_to_improve": ["More examples", "Technical depth"],
    "coaching_tips": ["Practice with real scenarios"]
  },
  "next_question_index": 2
}
```

#### End Session
```
POST /session/{session_id}/end_session
Authorization: Bearer {token}
Content-Type: application/json

Response:
{
  "session_id": 1,
  "status": "completed",
  "total_questions": 10,
  "final_score": 84.2,
  "performance_summary": {
    "correctness_avg": 82,
    "clarity_avg": 86,
    "confidence_avg": 84
  },
  "completed_at": "2026-04-15T11:15:00"
}
```

### Dashboard & Analytics

#### Get User Dashboard
```
GET /dashboard
Authorization: Bearer {token}

Response:
{
  "user_id": 1,
  "total_sessions": 5,
  "average_score": 82.3,
  "best_score": 92,
  "worst_score": 73,
  "skill_breakdown": {
    "correctness": 82,
    "clarity": 85,
    "confidence": 79
  },
  "recent_sessions": [
    {
      "session_id": 5,
      "date": "2026-04-15",
      "score": 84,
      "questions_answered": 10
    }
  ]
}
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in backend directory:

```env
# API Keys
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_key_here

# JWT
JWT_SECRET_KEY=your_secure_random_string_here

# Database
DATABASE_URL=sqlite:///./interview_prep.db

# Frontend
FRONTEND_URL=http://localhost:5173
```

### Advanced Configuration

#### Database Connection
```python
# SQLite (default, local development)
DATABASE_URL=sqlite:///./interview_prep.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/interview_prep
```

#### Question Generation
Edit `backend/services/adaptive_question_service.py`:
```python
DIFFICULTY_LEVELS = {
    1: "Beginner",      # Basic concepts
    2: "Junior",        # Practical understanding
    3: "Intermediate",  # Problem-solving
    4: "Senior",        # Architecture decisions
    5: "Expert"         # Edge cases & optimization
}

QUESTIONS_PER_SESSION = 10  # Adjust for interview length
QUESTION_TIMEOUT = 180      # Seconds per question
```

---

## 🐛 Troubleshooting

### Backend Issues

#### Backend won't start
```bash
# Check Python version
python --version  # Must be 3.10+

# Verify virtual environment
.venv/Scripts/Activate.ps1  # Windows
source .venv/bin/activate   # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check for port conflicts
netstat -tuln | grep 8000  # Linux
netstat -ano | findstr :8000  # Windows
```

#### API key errors
```
Error: GROQ_API_KEY not found

Solution:
1. Verify .env file exists in backend/
2. Check API keys are valid:
   - Groq: https://console.groq.com/keys
   - Gemini: https://aistudio.google.com
3. Restart backend after changing .env
```

#### Database errors
```
Error: database is locked / no such table

Solution:
# Delete existing database and reinitialize
rm backend/interview_prep.db
python -c "from database import init_db; init_db()"
```

### Frontend Issues

#### Frontend won't connect to backend
```bash
# Check VITE_API_URL in .env
cat frontend/.env
# Should be: VITE_API_URL=http://localhost:8000

# Verify backend is running
curl http://127.0.0.1:8000/docs

# Check CORS configuration in backend/main.py
```

#### Webcam/microphone permissions
```
Error: Unable to access camera/microphone

Solution:
1. Browser must be HTTPS (localhost is exception)
2. Grant permissions when prompted
3. Check browser privacy settings
4. Clear browser cache and try again
```

#### npm dependency issues
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules
rm -rf frontend/node_modules

# Reinstall
cd frontend
npm install
```

---

## 📈 Performance Metrics

### Typical Rankings

**Startup Time:**
- Backend: 3-5 seconds (with background model loading)
- Frontend: 2-3 seconds (dev mode)

**Question Generation:**
- Resume upload: 2-5 seconds
- Question generation: 3-8 seconds (depends on resume length)

**Answer Evaluation:**
- Audio analysis: 2-3 seconds
- Video analysis: 1-2 seconds
- Text evaluation: 2-4 seconds
- Total feedback: 5-10 seconds

**Model Sizes:**
- SBERT embeddings: ~500 MB (loaded once)
- MediaPipe model: ~20 MB
- LLM (Groq API): Cloud-based, no local storage

---

## 🔐 Security Considerations

1. **API Keys**: Never commit `.env` files. Use `.env.example` for templates.
2. **Passwords**: Hashed with bcrypt, never stored plain-text.
3. **JWT Tokens**: 30-minute expiration, refresh on login.
4. **CORS**: Configured to allow only `FRONTEND_URL`.
5. **SQL Injection**: Protected by SQLAlchemy ORM.
6. **File Upload**: Validated file types and sizes.

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Groq API Docs](https://groq.com/docs/)
- [Google Gemini Docs](https://ai.google.dev/)
- [MediaPipe Docs](https://mediapipe.dev/)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)

---

## 📝 License

This project is part of an academic FYP (Final Year Project). Use for educational purposes.

---

## 🤝 Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [API Documentation](#api-documentation)
3. Check backend logs: `backend/startup_log.txt`
4. Verify `.env` configuration

---

**Created:** April 2026  
**Status:** Fully Functional & Production-Ready  
**GitHub:** https://github.com/Faiz1310/AI-Interview-Training-System
