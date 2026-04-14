"""
========================================
FULL SYSTEM VALIDATION + FAILURE AUDIT
========================================
Tests 10 critical workflows.
Reports PASS/FAIL with root causes.
Author: QA Auditor
Mode: STRICT (no assumptions)
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sqlite3
import os
import traceback
from pathlib import Path

BASE_URL = "http://127.0.0.1:8001"  # Different port to avoid conflicts
TEST_RESULTS = []

def log_test(test_num, name, status, details, error=None):
    """Log individual test result"""
    result = {
        "test": test_num,
        "name": name,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "details": details,
        "error": error if error else None
    }
    TEST_RESULTS.append(result)
    
    status_symbol = "✓ PASS" if status == "PASS" else "✗ FAIL" if status == "FAIL" else "⊘ BLOCKED"
    print(f"\n{'='*60}")
    print(f"{status_symbol} TEST {test_num}: {name}")
    print(f"{'='*60}")
    print(f"Details: {details}")
    if error:
        print(f"Error: {error}")
    print(f"{'='*60}")

def verify_api_available():
    """Verify backend is responding"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=3)
        return response.status_code == 200
    except:
        return False

print("\n🔍 CHECKING BACKEND AVAILABILITY...")
if not verify_api_available():
    print("❌ Backend not responding on port 8001")
    print("Starting backend on port 8001...")
    os.system(f'cd "{os.path.dirname(__file__)}" && start python -m uvicorn main:app --port 8001')
    time.sleep(5)
    if not verify_api_available():
        print("❌ backend still not available. Exiting.")
        exit(1)
print("✓ Backend available")

# ============================================================================
# TEST 1: AUTH SYSTEM
# ============================================================================

test_email = f"audit_{int(time.time())}@test.com"
test_password = "TestAudit123!@#"
test_token = None
test_user_id = None

try:
    # Register
    r = requests.post(f"{BASE_URL}/register", json={
        "name": "Audit User",
        "email": test_email,
        "password": test_password
    })
    
    if r.status_code not in [200, 201]:
        log_test(1, "Auth System", "FAIL", 
                 f"Register failed: {r.status_code}",
                 f"Response: {r.text}")
    else:
        register_data = r.json()
        test_user_id = register_data.get("id")
        
        # Login
        login_r = requests.post(f"{BASE_URL}/login", json={
            "email": test_email,
            "password": test_password
        })
        
        if login_r.status_code != 200:
            log_test(1, "Auth System", "FAIL",
                     f"Login failed: {login_r.status_code}",
                     f"Response: {login_r.text}")
        else:
            login_data = login_r.json()
            test_token = login_data.get("access_token")
            
            if not test_token:
                log_test(1, "Auth System", "FAIL",
                         "Login succeeded but no token returned",
                         f"Response: {login_data}")
            else:
                # Verify token is usable
                headers = {"Authorization": f"Bearer {test_token}"}
                me_r = requests.get(f"{BASE_URL}/me", headers=headers)
                
                if me_r.status_code != 200:
                    log_test(1, "Auth System", "FAIL",
                             f"Token not usable in protected route: {me_r.status_code}",
                             f"Response: {me_r.text}")
                else:
                    me_data = me_r.json()
                    if me_data.get("email") != test_email:
                        log_test(1, "Auth System", "FAIL",
                                 "Token valid but email mismatch",
                                 f"Expected: {test_email}, Got: {me_data.get('email')}")
                    else:
                        log_test(1, "Auth System", "PASS",
                                 f"Register → Login → Token verified for {test_email}",
                                 None)
except Exception as e:
    log_test(1, "Auth System", "FAIL",
             f"Exception in auth flow",
             f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 2: RESUME PIPELINE
# ============================================================================

test_resume_id = None

if not test_token:
    log_test(2, "Resume Pipeline", "BLOCKED",
             "Cannot proceed: auth token unavailable",
             None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Create test resume content
        resume_text = """
John Doe
Senior Python Developer

SKILLS:
- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL
- React.js
- Docker

EXPERIENCE:
- 5 years Python development
- Built microservices with FastAPI
- Database optimization with SQLAlchemy
"""
        
        jd_text = """
Senior Python Developer - Fintech

Required:
- 5+ years Python experience
- FastAPI expertise
- SQL databases
- API design
"""
        
        # Upload resume
        files = {
            "resume_file": ("resume.txt", resume_text),
            "jd_file": ("jd.txt", jd_text)
        }
        data = {
            "job_role": "Senior Python Developer",
            "company": "Audit Test Co"
        }
        
        r = requests.post(f"{BASE_URL}/upload_resume", headers=headers, files=files, data=data)
        
        if r.status_code != 200:
            log_test(2, "Resume Pipeline", "FAIL",
                     f"Upload failed: {r.status_code}",
                     f"Response: {r.text}")
        else:
            resume_data = r.json()
            test_resume_id = resume_data.get("id")
            
            if not test_resume_id:
                log_test(2, "Resume Pipeline", "FAIL",
                         "Upload succeeded but no resume ID returned",
                         f"Response: {resume_data}")
            else:
                # Verify resume in DB
                try:
                    from database import SessionLocal
                    from models.resume import Resume
                    
                    db = SessionLocal()
                    resume = db.query(Resume).filter(Resume.id == test_resume_id).first()
                    db.close()
                    
                    if not resume:
                        log_test(2, "Resume Pipeline", "FAIL",
                                 "Resume saved in API but not found in DB",
                                 f"Resume ID: {test_resume_id}")
                    elif resume.user_id != test_user_id:
                        log_test(2, "Resume Pipeline", "FAIL",
                                 "Resume not linked to user",
                                 f"Expected user_id: {test_user_id}, Got: {resume.user_id}")
                    else:
                        log_test(2, "Resume Pipeline", "PASS",
                                 f"Resume uploaded, stored in DB, linked to user {test_user_id}",
                                 None)
                except Exception as e:
                    log_test(2, "Resume Pipeline", "FAIL",
                             "Could not verify in DB",
                             f"{type(e).__name__}: {str(e)}")
                
except Exception as e:
    log_test(2, "Resume Pipeline", "FAIL",
             "Exception in resume pipeline",
             f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 3: INTERVIEW START
# ============================================================================

test_session_id = None

if not test_token or not test_resume_id:
    log_test(3, "Interview Start", "BLOCKED",
             "Cannot proceed: token or resume ID unavailable",
             None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        r = requests.post(f"{BASE_URL}/start_session", headers=headers, json={
            "resume_id": test_resume_id,
            "total_questions": 5,
            "difficulty_level": 2
        })
        
        if r.status_code != 200:
            log_test(3, "Interview Start", "FAIL",
                     f"Start session failed: {r.status_code}",
                     f"Response: {r.text}")
            test_session_id = None
        else:
            session_data = r.json()
            test_session_id = session_data.get("session_id")
            
            if not test_session_id:
                log_test(3, "Interview Start", "FAIL",
                         "Session created but no session_id returned",
                         f"Response: {session_data}")
            else:
                log_test(3, "Interview Start", "PASS",
                         f"Session started: {test_session_id}",
                         None)
                
except Exception as e:
    log_test(3, "Interview Start", "FAIL",
             "Exception in interview start",
             f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
    test_session_id = None

# ============================================================================
# TEST 4: QUESTION FLOW (ADAPTIVE ENGINE)
# ============================================================================

if not test_token or not test_session_id:
    log_test(4, "Question Flow", "BLOCKED",
             "Cannot proceed: token or session ID unavailable",
             None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Get first question
        r1 = requests.get(f"{BASE_URL}/get_question/{test_session_id}", headers=headers)
        
        if r1.status_code != 200:
            log_test(4, "Question Flow", "FAIL",
                     f"Get question failed: {r1.status_code}",
                     f"Response: {r1.text}")
        else:
            q1_data = r1.json()
            q1_text = q1_data.get("question_text")
            q1_id = q1_data.get("question_id")
            
            if not q1_text or len(q1_text.strip()) == 0:
                log_test(4, "Question Flow", "FAIL",
                         "Question returned but text is empty",
                         f"Response: {q1_data}")
            elif len(q1_text) < 10:
                log_test(4, "Question Flow", "FAIL",
                         "Question text is suspiciously short",
                         f"Text: '{q1_text}'")
            elif "python" not in q1_text.lower() and "developer" not in q1_text.lower():
                log_test(4, "Question Flow", "FAIL",
                         "Question not derived from resume context (should mention Python/Developer)",
                         f"Question: {q1_text}")
            else:
                # Submit answer to first question
                r_submit = requests.post(f"{BASE_URL}/submit_answer", headers=headers, json={
                    "session_id": test_session_id,
                    "question_id": q1_id,
                    "answer_text": "I have 5 years of experience with Python and FastAPI.",
                    "transcription": "I have 5 years of experience with Python and FastAPI.",
                    "video_features": {}
                })
                
                if r_submit.status_code != 200:
                    log_test(4, "Question Flow", "FAIL",
                             f"Submit answer failed: {r_submit.status_code}",
                             f"Response: {r_submit.text}")
                else:
                    # Get second question
                    r2 = requests.get(f"{BASE_URL}/get_question/{test_session_id}", headers=headers)
                    
                    if r2.status_code != 200:
                        log_test(4, "Question Flow", "FAIL",
                                 f"Get second question failed: {r2.status_code}",
                                 f"Response: {r2.text}")
                    else:
                        q2_data = r2.json()
                        q2_text = q2_data.get("question_text")
                        
                        if q2_text == q1_text:
                            log_test(4, "Question Flow", "FAIL",
                                     "Same question repeated (no adaptation)",
                                     f"Q1: {q1_text}\nQ2: {q2_text}")
                        elif not q2_text or len(q2_text.strip()) == 0:
                            log_test(4, "Question Flow", "FAIL",
                                     "Second question is empty",
                                     f"Response: {q2_data}")
                        else:
                            log_test(4, "Question Flow", "PASS",
                                     f"Questions generated and adapted (Q1 != Q2)",
                                     f"Q1: {q1_text[:60]}...\nQ2: {q2_text[:60]}...")
                            
    except Exception as e:
        log_test(4, "Question Flow", "FAIL",
                 "Exception in question flow",
                 f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 5: SESSION COMPLETION
# ============================================================================

if not test_token or not test_session_id:
    log_test(5, "Session Completion", "BLOCKED",
             "Cannot proceed: token or session ID unavailable",
             None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Complete interview
        r = requests.post(f"{BASE_URL}/complete_interview", headers=headers, json={
            "session_id": test_session_id
        })
        
        if r.status_code != 200:
            log_test(5, "Session Completion", "FAIL",
                     f"Complete interview failed: {r.status_code}",
                     f"Response: {r.text}")
        else:
            # Verify session status in DB
            try:
                from database import SessionLocal
                from models.session import InterviewSession
                
                db = SessionLocal()
                session = db.query(InterviewSession).filter(
                    InterviewSession.id == test_session_id
                ).first()
                db.close()
                
                if not session:
                    log_test(5, "Session Completion", "FAIL",
                             "Session not found in DB",
                             f"Session ID: {test_session_id}")
                elif session.status != "completed":
                    log_test(5, "Session Completion", "FAIL",
                             f"Session status not updated (expected 'completed', got '{session.status}')",
                             f"Session ID: {test_session_id}")
                else:
                    log_test(5, "Session Completion", "PASS",
                             f"Session completed and status updated in DB",
                             None)
            except Exception as e:
                log_test(5, "Session Completion", "FAIL",
                         "Could not verify in DB",
                         f"{type(e).__name__}: {str(e)}")
                         
    except Exception as e:
        log_test(5, "Session Completion", "FAIL",
                 "Exception in session completion",
                 f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 6: FEEDBACK SYSTEM
# ============================================================================

if not test_token or not test_session_id:
    log_test(6, "Feedback System", "BLOCKED",
             "Cannot proceed: token or session ID unavailable",
             None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        r = requests.get(f"{BASE_URL}/session/{test_session_id}/feedback", headers=headers)
        
        if r.status_code != 200:
            log_test(6, "Feedback System", "FAIL",
                     f"Get feedback failed: {r.status_code}",
                     f"Response: {r.text}")
        else:
            feedback_data = r.json()
            
            # Check required fields
            required_fields = [
                "score_breakdown",
                "overall_score",
                "strengths",
                "weaknesses",
                "recommendations"
            ]
            
            missing_fields = [f for f in required_fields if f not in feedback_data or feedback_data[f] is None]
            
            if missing_fields:
                log_test(6, "Feedback System", "FAIL",
                         f"Feedback missing fields: {missing_fields}",
                         f"Response: {json.dumps(feedback_data, indent=2)}")
            else:
                score_breakdown = feedback_data.get("score_breakdown", {})
                metrics = ["correctness", "clarity", "confidence"]
                missing_metrics = [m for m in metrics if m not in score_breakdown]
                
                if missing_metrics:
                    log_test(6, "Feedback System", "FAIL",
                             f"Score breakdown missing metrics: {missing_metrics}",
                             f"Breakdown: {score_breakdown}")
                else:
                    # Check for NaN/null/invalid values
                    invalid_values = []
                    for metric, value in score_breakdown.items():
                        if value is None or (isinstance(value, float) and (value != value)):  # NaN check
                            invalid_values.append(f"{metric}={value}")
                    
                    if invalid_values:
                        log_test(6, "Feedback System", "FAIL",
                                 f"Invalid values in score breakdown: {invalid_values}",
                                 f"Breakdown: {score_breakdown}")
                    else:
                        log_test(6, "Feedback System", "PASS",
                                 f"Feedback complete with all metrics: {score_breakdown}",
                                 None)
                         
    except Exception as e:
        log_test(6, "Feedback System", "FAIL",
                 "Exception in feedback system",
                 f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 7: DASHBOARD & SOFT DELETE
# ============================================================================

if not test_token:
    log_test(7, "Dashboard & Soft Delete", "BLOCKED",
             "Cannot proceed: token unavailable",
             None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Get sessions before delete
        r_before = requests.get(f"{BASE_URL}/sessions", headers=headers)
        
        if r_before.status_code != 200:
            log_test(7, "Dashboard & Soft Delete", "FAIL",
                     f"Get sessions failed: {r_before.status_code}",
                     f"Response: {r_before.text}")
        else:
            sessions_before = r_before.json()
            count_before = len(sessions_before) if isinstance(sessions_before, list) else 0
            
            if test_session_id:
                # Delete session
                r_delete = requests.delete(f"{BASE_URL}/session/{test_session_id}", headers=headers)
                
                if r_delete.status_code != 200:
                    log_test(7, "Dashboard & Soft Delete", "FAIL",
                             f"Delete session failed: {r_delete.status_code}",
                             f"Response: {r_delete.text}")
                else:
                    # Get sessions after delete
                    time.sleep(0.5)
                    r_after = requests.get(f"{BASE_URL}/sessions", headers=headers)
                    
                    if r_after.status_code != 200:
                        log_test(7, "Dashboard & Soft Delete", "FAIL",
                                 f"Get sessions after delete failed: {r_after.status_code}",
                                 f"Response: {r_after.text}")
                    else:
                        sessions_after = r_after.json()
                        count_after = len(sessions_after) if isinstance(sessions_after, list) else 0
                        
                        if count_after >= count_before:
                            log_test(7, "Dashboard & Soft Delete", "FAIL",
                                     f"Session not hidden after delete (before={count_before}, after={count_after})",
                                     f"Sessions after delete: {sessions_after}")
                        else:
                            # Try restore
                            r_restore = requests.post(f"{BASE_URL}/session/{test_session_id}/restore", headers=headers)
                            
                            if r_restore.status_code != 200:
                                log_test(7, "Dashboard & Soft Delete", "FAIL",
                                         f"Restore session failed: {r_restore.status_code}",
                                         f"Response: {r_restore.text}")
                            else:
                                time.sleep(0.5)
                                r_restored = requests.get(f"{BASE_URL}/sessions", headers=headers)
                                
                                if r_restored.status_code == 200:
                                    sessions_restored = r_restored.json()
                                    count_restored = len(sessions_restored) if isinstance(sessions_restored, list) else 0
                                    
                                    if count_restored == count_before:
                                        log_test(7, "Dashboard & Soft Delete", "PASS",
                                                 f"Soft delete hid session, restore brought it back",
                                                 None)
                                    else:
                                        log_test(7, "Dashboard & Soft Delete", "FAIL",
                                                 f"Restore failed (before={count_before}, restored={count_restored})",
                                                 None)
                                else:
                                    log_test(7, "Dashboard & Soft Delete", "FAIL",
                                             f"Get sessions after restore failed: {r_restored.status_code}",
                                             None)
            else:
                log_test(7, "Dashboard & Soft Delete", "BLOCKED",
                         "No session ID to test delete",
                         None)
                         
    except Exception as e:
        log_test(7, "Dashboard & Soft Delete", "FAIL",
                 "Exception in dashboard/soft delete",
                 f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 8: BEHAVIOR METRICS VALIDATION
# ============================================================================

if not test_session_id:
    log_test(8, "Behavior Metrics Validation", "BLOCKED",
             "Cannot proceed: no session ID",
             None)
else:
    try:
        from database import SessionLocal
        from models.behavior_metric import BehaviorMetric
        
        db = SessionLocal()
        metrics = db.query(BehaviorMetric).filter(
            BehaviorMetric.session_id == test_session_id
        ).all()
        db.close()
        
        if not metrics:
            log_test(8, "Behavior Metrics Validation", "FAIL",
                     "No behavior metrics recorded for session",
                     f"Session ID: {test_session_id}")
        else:
            metric = metrics[0]
            
            # Check attention_score
            attention_score = getattr(metric, "attention_score", None)
            
            if attention_score is None:
                log_test(8, "Behavior Metrics Validation", "FAIL",
                         "attention_score is None",
                         f"Metric data: {vars(metric)}")
            elif not (0 <= attention_score <= 100):
                log_test(8, "Behavior Metrics Validation", "FAIL",
                         f"attention_score out of range: {attention_score}",
                         f"Expected: 0-100")
            else:
                # Check counts
                looking_away_count = getattr(metric, "looking_away_count", 0)
                face_absent_count = getattr(metric, "face_absent_count", 0)
                multiple_faces_count = getattr(metric, "multiple_faces_detected", 0)
                
                if not isinstance(looking_away_count, (int, float)):
                    log_test(8, "Behavior Metrics Validation", "FAIL",
                             f"looking_away_count is not numeric: {looking_away_count}",
                             None)
                else:
                    log_test(8, "Behavior Metrics Validation", "PASS",
                             f"Behavior metrics valid: attention={attention_score}, looking_away={looking_away_count}",
                             None)
                         
    except Exception as e:
        log_test(8, "Behavior Metrics Validation", "FAIL",
                 "Exception checking behavior metrics",
                 f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 9: AUDIO TRANSCRIPTION
# ============================================================================

if not test_token or not test_session_id:
    log_test(9, "Audio Transcription", "BLOCKED",
             "Cannot proceed: token or session ID unavailable",
             None)
else:
    try:
        from database import SessionLocal
        from models.answer import InterviewAnswer
        
        db = SessionLocal()
        answers = db.query(InterviewAnswer).filter(
            InterviewAnswer.session_id == test_session_id
        ).all()
        db.close()
        
        if not answers:
            log_test(9, "Audio Transcription", "FAIL",
                     "No answers found for session",
                     f"Session ID: {test_session_id}")
        else:
            answer = answers[0]
            transcription = answer.transcription if hasattr(answer, 'transcription') else None
            
            if not transcription or len(transcription.strip()) == 0:
                log_test(9, "Audio Transcription", "FAIL",
                         "Transcription is empty or missing",
                         f"Answer: {vars(answer)}")
            else:
                log_test(9, "Audio Transcription", "PASS",
                         f"Transcription recorded: {transcription[:50]}...",
                         None)
                         
    except Exception as e:
        log_test(9, "Audio Transcription", "FAIL",
                 "Exception checking transcription",
                 f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# TEST 10: FORGOT PASSWORD
# ============================================================================

try:
    # Request password reset
    reset_email = test_email
    r_forgot = requests.post(f"{BASE_URL}/forgot_password", json={
        "email": reset_email
    })
    
    if r_forgot.status_code != 200:
        log_test(10, "Forgot Password", "FAIL",
                 f"Forgot password request failed: {r_forgot.status_code}",
                 f"Response: {r_forgot.text}")
    else:
        forgot_data = r_forgot.json()
        reset_token = forgot_data.get("reset_token")
        
        if not reset_token:
            log_test(10, "Forgot Password", "FAIL",
                     "Password reset requested but no token returned",
                     f"Response: {forgot_data}")
        else:
            # Reset password with token
            new_password = "NewAudit456!@#"
            r_reset = requests.post(f"{BASE_URL}/reset_password", json={
                "token": reset_token,
                "new_password": new_password
            })
            
            if r_reset.status_code != 200:
                log_test(10, "Forgot Password", "FAIL",
                         f"Password reset failed: {r_reset.status_code}",
                         f"Response: {r_reset.text}")
            else:
                # Try login with new password
                r_login = requests.post(f"{BASE_URL}/login", json={
                    "email": reset_email,
                    "password": new_password
                })
                
                if r_login.status_code != 200:
                    log_test(10, "Forgot Password", "FAIL",
                             f"Login with new password failed: {r_login.status_code}",
                             f"Response: {r_login.text}")
                else:
                    log_test(10, "Forgot Password", "PASS",
                             f"Password reset and login with new password successful",
                             None)
                         
except Exception as e:
    log_test(10, "Forgot Password", "FAIL",
             "Exception in forgot password flow",
             f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

# ============================================================================
# FINAL REPORT
# ============================================================================

print("\n\n")
print("="*80)
print("FULL SYSTEM VALIDATION AUDIT - FINAL REPORT")
print("="*80)
print(f"Timestamp: {datetime.now().isoformat()}")
print(f"Total Tests: {len(TEST_RESULTS)}")

passed = [t for t in TEST_RESULTS if t["status"] == "PASS"]
failed = [t for t in TEST_RESULTS if t["status"] == "FAIL"]
blocked = [t for t in TEST_RESULTS if t["status"] == "BLOCKED"]

print(f"PASSED: {len(passed)}/10")
print(f"FAILED: {len(failed)}/10")
print(f"BLOCKED: {len(blocked)}/10")

print("\n" + "="*80)
print("TEST-BY-TEST RESULTS")
print("="*80)

for result in TEST_RESULTS:
    status_symbol = "✓" if result["status"] == "PASS" else "✗" if result["status"] == "FAIL" else "⊘"
    print(f"\n{status_symbol} TEST {result['test']}: {result['name']}")
    print(f"   Status: {result['status']}")
    print(f"   Details: {result['details']}")
    if result['error']:
        print(f"   Error: {result['error'][:200]}...")

print("\n" + "="*80)
print("CRITICAL ISSUES")
print("="*80)

if failed:
    print(f"\nFound {len(failed)} FAILING tests:\n")
    for result in failed:
        print(f"  TEST {result['test']}: {result['name']}")
        print(f"    → {result['details']}")
        print(f"    → {result['error'][:150] if result['error'] else 'No error detail'}")
        print()
else:
    print("\n✓ No critical failures!")

print("\n" + "="*80)
print("FINAL VERDICT")
print("="*80)

if len(passed) == 10:
    verdict = "🟢 STABLE"
    recommendation = "System is PRODUCTION READY"
elif len(passed) >= 7:
    verdict = "🟡 PARTIALLY STABLE"
    recommendation = f"System partially working. {len(failed)} tests failing. Requires fixes before production."
else:
    verdict = "🔴 UNSTABLE"
    recommendation = f"System is NOT READY. {len(failed)} critical failures. Extensive debugging required."

print(f"Status: {verdict}")
print(f"Recommendation: {recommendation}")
print(f"Pass Rate: {len(passed)}/10 ({int(len(passed)*10)}%)")

print("\n" + "="*80)

with open("validation_audit_report.json", "w") as f:
    json.dump(TEST_RESULTS, f, indent=2)
    print(f"Full report saved to: validation_audit_report.json")
