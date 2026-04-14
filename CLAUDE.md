AI Interview System – Full Iterative Implementation Prompt
# Multimodal AI Interview Training System – Architecture Upgrade & Implementation Prompt

You are a **Senior AI Architect, ML Engineer, and Full-Stack Developer**.

Your task is to **upgrade an existing partially implemented AI Interview Training System**.

IMPORTANT RULES

1. The project already has partial implementation.
2. You must **analyze the existing codebase first**.
3. You must **refactor and extend the project**, not blindly rewrite it.
4. Follow the **new architecture described below**, even if the existing implementation differs.

The implementation must happen in **strict iterative phases**.

---

# PROJECT OBJECTIVE

Build a **Multimodal AI Interview Training Platform** that acts as a training coach rather than a simple evaluator.

The system must evaluate candidates using **three independent dimensions**:

• Correctness (knowledge accuracy)  
• Clarity (quality of explanation)  
• Confidence (behavioral delivery)

These dimensions must remain **strictly decoupled**.

Confidence must **never reduce correctness scores**.

The system must support **continuous improvement across multiple interview sessions**.

---

# CORE FEATURES

The system must include the following modules:

### Resume + Job Description Processing
Users upload:

• Resume (PDF / DOC / text)  
• Job description (PDF / DOC / text)

The system must:

• extract text
• clean and chunk content
• generate semantic embeddings
• store embeddings in a vector database

---

### Resume-Driven Question Generation (RAG)

The system generates interview questions using:

• resume content
• job description requirements

The RAG pipeline should retrieve relevant chunks and inject them into an LLM.

Types of questions generated:

• skill alignment questions  
• gap analysis questions  
• project-depth questions  

---

### Conversational AI Interviewer

The system should simulate an interviewer.

Capabilities:

• ask questions sequentially  
• maintain interview state  
• provide conversational pacing  
• optionally deliver questions via TTS  

---

### Speech-to-Text Processing

Candidate responses are captured via microphone.

Use:

Whisper ASR or browser speech recognition.

The transcription is sent to the backend for evaluation.

---

### Audio Behavioral Analysis

Extract prosodic features including:

• speech rate  
• pause duration  
• pitch variation  
• energy variation  

Libraries:

librosa or equivalent.

These features contribute **only to confidence estimation**.

---

### Video Behavioral Analysis

Webcam video is captured during the interview.

Use:

MediaPipe FaceMesh.

Extract features:

• eye contact ratio  
• blink rate  
• head stability  
• facial stress indicators  
• gaze direction  

Optionally include:

CNN-based Facial Emotion Recognition.

Video features contribute **only to confidence estimation**.

---

### Text Answer Evaluation

LLM-based structured evaluation must produce:

• correctness score  
• covered concepts  
• missing points  
• incorrect statements  
• qualitative feedback  

This evaluation must prioritize **knowledge accuracy**.

---

### Clarity Analysis

Evaluate:

• logical flow  
• explanation structure  
• redundancy  
• sentence completeness  

Clarity must remain **independent of correctness and confidence**.

---

### Multimodal Confidence Fusion

Confidence must be computed using:

• audio cues  
• video cues  
• text hesitation indicators  

Example:

Confidence = weighted fusion of behavioral indicators.

---

### Hierarchical Scoring Strategy

Final evaluation must follow:

Level 1 — Multimodal Confidence Fusion  
Level 2 — Training Performance Score

Example weighting:

Final Score =

0.50 Correctness  
0.30 Clarity  
0.20 Confidence

---

### Real-Time Supportive Feedback

When hesitation or stress is detected, the system should provide encouragement:

Examples:

“Take a moment and explain step by step.”  
“You're doing well, continue calmly.”

Feedback must be **supportive and non-judgmental**.

---

### Progress Tracking

The system must store:

• session scores  
• correctness trends  
• clarity trends  
• confidence improvement  

Dashboard analytics must show:

• performance trends  
• radar skill charts  
• improvement recommendations  

---

# SYSTEM ARCHITECTURE (MANDATORY)

The implementation must follow this architecture.


Frontend (React)
│
├── Webcam Capture
├── Microphone Capture
├── Speech Recognition
└── Interview UI
│
▼
Edge Processing (Browser)
│
├── MediaPipe behavioral feature extraction
├── basic audio metrics
└── speech transcription
│
▼
Backend (FastAPI)
│
├── Resume Analysis (Gemini)
├── Question Generation (Groq)
├── Text Evaluation
├── Audio Analyzer
├── Video Analyzer
├── Multimodal Fusion Engine
└── Feedback Generator
│
▼
Database + Analytics Dashboard


---

# TECHNOLOGY STACK

Frontend

React  
MediaPipe  
Web Speech API  
WebRTC  
Chart.js  

Backend

FastAPI  
Python  
SQLAlchemy  
JWT authentication  

AI

Gemini API – resume analysis  
Groq API – question generation  
SentenceTransformers – semantic similarity  
librosa – audio analysis  
MediaPipe – video analysis  

---

# IMPLEMENTATION PHASES

The system must be implemented in the following order.

---

## Phase 1 – Codebase Analysis

Analyze the existing repository.

Produce a report containing:

• existing modules  
• missing modules  
• broken components  
• architecture differences  

Wait for confirmation before continuing.

---

## Phase 2 – Architecture Refactoring

Refactor the codebase to match the architecture above.

Define:

• folder structure  
• API routes  
• AI module interfaces  

---

## Phase 3 – Backend Implementation

Implement FastAPI backend.

Required modules:

routes/

auth.py  
resume.py  
questions.py  
sessions.py  
dashboard.py  

AI modules:

video_analyzer.py  
audio_analyzer.py  
text_evaluator.py  
fusion_engine.py  
feedback_generator.py  

---

## Phase 4 – AI Module Implementation

Implement:

• behavioral feature processing  
• audio feature extraction  
• LLM evaluation  
• multimodal scoring  

---

## Phase 5 – Frontend Implementation

Build the interview UI.

Features:

• webcam capture  
• microphone capture  
• speech transcription  
• real-time interview interface  

---

## Phase 6 – System Integration

Connect frontend and backend.

Workflow:

Login  
Upload Resume  
Generate Questions  
Start Interview  
Submit Answers  
Evaluate Responses  
Display Feedback  

---

## Phase 7 – Dashboard Analytics

Implement performance tracking.

Visualizations:

• score trends  
• radar skill charts  
• improvement insights  

---

# ERROR HANDLING REQUIREMENTS

The system must:

• handle AI API failures  
• implement fallback scoring  
• log errors properly  
• handle missing audio/video  

---

# FINAL OUTPUT

The system must generate a **fully runnable project** including:

• backend code  
• frontend code  
• AI modules  
• database schema  
• API integrations  
• dashboard  

All components must integrate correctly with the existing project.