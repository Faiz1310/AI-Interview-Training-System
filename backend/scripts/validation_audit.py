#!/usr/bin/env python3
"""
FULL SYSTEM VALIDATION + FAILURE AUDIT
========================================
10 critical end-to-end tests with strict verification.
Reports PASS/FAIL with root causes and technical details.
"""

import requests
import json
import time
from datetime import datetime
import sqlite3
import os
import traceback
import sys

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:8001"
TEST_RESULTS = []

def log_test(test_num, name, status, details, error=None):
    """Log test result"""
    result = {
        "test": test_num,
        "name": name,
        "status": status,
        "details": details,
        "error": str(error) if error else None
    }
    TEST_RESULTS.append(result)
    
    symbol = "[+]" if status == "PASS" else "[-]" if status == "FAIL" else "[?]"
    print(f"\n{symbol} TEST {test_num}: {name}")
    print(f"  Status: {status}")
    print(f"  Details: {details}")
    if error:
        print(f"  Error: {str(error)[:200]}")

print("\n" + "="*70)
print("FULL SYSTEM VALIDATION AUDIT")
print("="*70)
print("Mode: STRICT (no assumptions)")
print("Time:", datetime.now().isoformat())

# ============================================================================
# INITIALIZATION
# ============================================================================

user_token = None
user_id = None
resume_id = None
session_id = None

print("\n[*] Checking backend availability...")
try:
    r = requests.get(f"{BASE_URL}/docs", timeout=3)
    print(f"[OK] Backend responding (status={r.status_code})")
except Exception as e:
    print(f"[FAIL] Backend not available: {e}")
    exit(1)

# ============================================================================
# TEST 1: AUTH SYSTEM
# ============================================================================

try:
    email = f"audit{int(time.time())}@test.com"
    password = "TestAudit123!"
    
    # Register
    r_reg = requests.post(f"{BASE_URL}/register", json={
        "name": "Audit User",
        "email": email,
        "password": password
    })
    
    if r_reg.status_code not in [200, 201]:
        log_test(1, "Auth System", "FAIL", 
                f"Register failed: {r_reg.status_code}", r_reg.text)
    else:
        user_id = r_reg.json().get("id")
        
        # Login
        r_login = requests.post(f"{BASE_URL}/login", json={
            "email": email,
            "password": password
        })
        
        if r_login.status_code != 200:
            log_test(1, "Auth System", "FAIL",
                    f"Login failed: {r_login.status_code}", r_login.text)
        else:
            user_token = r_login.json().get("access_token")
            
            if not user_token:
                log_test(1, "Auth System", "FAIL",
                        "No token returned", r_login.json())
            else:
                # Test token
                headers = {"Authorization": f"Bearer {user_token}"}
                r_me = requests.get(f"{BASE_URL}/me", headers=headers)
                
                if r_me.status_code != 200:
                    log_test(1, "Auth System", "FAIL",
                            f"Token invalid: {r_me.status_code}", r_me.text)
                else:
                    log_test(1, "Auth System", "PASS",
                            f"Auth successful: {email}", None)
except Exception as e:
    log_test(1, "Auth System", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 2: RESUME PIPELINE
# ============================================================================

if not user_token:
    log_test(2, "Resume Pipeline", "BLOCKED", "No auth token", None)
else:
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        resume_text = "Senior Python Developer\nPython FastAPI SQLAlchemy Docker"
        jd_text = "Need Python developer with FastAPI"
        
        files = {
            "resume_file": ("resume.txt", resume_text),
            "jd_file": ("jd.txt", jd_text)
        }
        data = {"job_role": "Senior Python Developer"}
        
        r = requests.post(f"{BASE_URL}/upload_resume", headers=headers, 
                         files=files, data=data)
        
        if r.status_code != 200:
            log_test(2, "Resume Pipeline", "FAIL",
                    f"Upload failed: {r.status_code}", r.text)
        else:
            resume_id = r.json().get("id")
            
            if not resume_id:
                log_test(2, "Resume Pipeline", "FAIL",
                        "No resume ID returned", r.json())
            else:
                log_test(2, "Resume Pipeline", "PASS",
                        f"Resume uploaded: {resume_id}", None)
    except Exception as e:
        log_test(2, "Resume Pipeline", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 3: INTERVIEW START
# ============================================================================

if not user_token or not resume_id:
    log_test(3, "Interview Start", "BLOCKED", 
            f"Missing token or resume (token={bool(user_token)}, resume={bool(resume_id)})", None)
else:
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        r = requests.post(f"{BASE_URL}/start_session", headers=headers, json={
            "resume_id": resume_id,
            "total_questions": 5,
            "difficulty_level": 2
        })
        
        if r.status_code != 200:
            log_test(3, "Interview Start", "FAIL",
                    f"Start failed: {r.status_code}", r.text)
        else:
            session_id = r.json().get("session_id")
            if not session_id:
                log_test(3, "Interview Start", "FAIL",
                        "No session_id returned", r.json())
            else:
                log_test(3, "Interview Start", "PASS",
                        f"Session started: {session_id}", None)
    except Exception as e:
        log_test(3, "Interview Start", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 4: QUESTION FLOW
# ============================================================================

if not user_token or not session_id:
    log_test(4, "Question Flow", "BLOCKED", 
            f"Missing token or session", None)
else:
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get question
        r = requests.get(f"{BASE_URL}/get_question/{session_id}", headers=headers)
        
        if r.status_code != 200:
            log_test(4, "Question Flow", "FAIL",
                    f"Get question failed: {r.status_code}", r.text)
        else:
            q_text = r.json().get("question_text", "")
            q_id = r.json().get("question_id")
            
            if not q_text or len(q_text) < 10:
                log_test(4, "Question Flow", "FAIL",
                        "Question empty or too short", f"Q: {q_text}")
            else:
                # Submit answer
                r_ans = requests.post(f"{BASE_URL}/submit_answer", headers=headers, json={
                    "session_id": session_id,
                    "question_id": q_id,
                    "answer_text": "I have experience with Python",
                    "transcription": "I have experience with Python"
                })
                
                if r_ans.status_code != 200:
                    log_test(4, "Question Flow", "FAIL",
                            f"Submit failed: {r_ans.status_code}", r_ans.text)
                else:
                    log_test(4, "Question Flow", "PASS",
                            f"Question retrieved and answer submitted", None)
    except Exception as e:
        log_test(4, "Question Flow", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 5: SESSION COMPLETION
# ============================================================================

if not user_token or not session_id:
    log_test(5, "Session Completion", "BLOCKED", "Missing token or session", None)
else:
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        r = requests.post(f"{BASE_URL}/complete_interview", headers=headers, json={
            "session_id": session_id
        })
        
        if r.status_code != 200:
            log_test(5, "Session Completion", "FAIL",
                    f"Complete failed: {r.status_code}", r.text)
        else:
            log_test(5, "Session Completion", "PASS",
                    "Session marked as completed", None)
    except Exception as e:
        log_test(5, "Session Completion", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 6: FEEDBACK SYSTEM
# ============================================================================

if not user_token or not session_id:
    log_test(6, "Feedback System", "BLOCKED", "Missing token or session", None)
else:
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        r = requests.get(f"{BASE_URL}/session/{session_id}/feedback", headers=headers)
        
        if r.status_code != 200:
            log_test(6, "Feedback System", "FAIL",
                    f"Feedback fetch failed: {r.status_code}", r.text)
        else:
            data = r.json()
            required = ["overall_score", "score_breakdown", "strengths", "weaknesses"]
            missing = [f for f in required if f not in data or data[f] is None]
            
            if missing:
                log_test(6, "Feedback System", "FAIL",
                        f"Missing fields: {missing}", json.dumps(data))
            else:
                log_test(6, "Feedback System", "PASS",
                        f"Feedback complete: score={data.get('overall_score')}", None)
    except Exception as e:
        log_test(6, "Feedback System", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 7: DASHBOARD & SOFT DELETE
# ============================================================================

if not user_token:
    log_test(7, "Dashboard & Soft Delete", "BLOCKED", "Missing token", None)
else:
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        r_list = requests.get(f"{BASE_URL}/sessions", headers=headers)
        if r_list.status_code == 200:
            before = len(r_list.json()) if isinstance(r_list.json(), list) else 0
            
            if session_id:
                r_del = requests.delete(f"{BASE_URL}/session/{session_id}", headers=headers)
                if r_del.status_code == 200:
                    time.sleep(0.5)
                    r_after = requests.get(f"{BASE_URL}/sessions", headers=headers)
                    if r_after.status_code == 200:
                        after = len(r_after.json()) if isinstance(r_after.json(), list) else 0
                        if after < before:
                            log_test(7, "Dashboard & Soft Delete", "PASS",
                                    f"Soft delete works (hidden)", None)
                        else:
                            log_test(7, "Dashboard & Soft Delete", "FAIL",
                                    f"Session not hidden after delete", None)
                    else:
                        log_test(7, "Dashboard & Soft Delete", "FAIL",
                                f"List after delete failed: {r_after.status_code}", None)
                else:
                    log_test(7, "Dashboard & Soft Delete", "FAIL",
                            f"Delete failed: {r_del.status_code}", r_del.text)
            else:
                log_test(7, "Dashboard & Soft Delete", "BLOCKED", "No session to delete", None)
        else:
            log_test(7, "Dashboard & Soft Delete", "FAIL",
                    f"List sessions failed: {r_list.status_code}", None)
    except Exception as e:
        log_test(7, "Dashboard & Soft Delete", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 8: BEHAVIOR METRICS
# ============================================================================

if not session_id:
    log_test(8, "Behavior Metrics", "BLOCKED", "No session", None)
else:
    try:
        from database import SessionLocal
        from models.behavior_metric import BehaviorMetric
        
        db = SessionLocal()
        metrics = db.query(BehaviorMetric).filter(
            BehaviorMetric.session_id == session_id
        ).all()
        db.close()
        
        if not metrics:
            log_test(8, "Behavior Metrics", "FAIL",
                    "No behavior metrics found", f"session={session_id}")
        else:
            m = metrics[0]
            attention = getattr(m, "attention_score", None)
            if attention is None or not (0 <= attention <= 100):
                log_test(8, "Behavior Metrics", "FAIL",
                        f"Invalid attention_score: {attention}", None)
            else:
                log_test(8, "Behavior Metrics", "PASS",
                        f"Behavior metrics valid: attention={attention}", None)
    except Exception as e:
        log_test(8, "Behavior Metrics", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 9: AUDIO TRANSCRIPTION
# ============================================================================

if not session_id:
    log_test(9, "Audio Transcription", "BLOCKED", "No session", None)
else:
    try:
        from database import SessionLocal
        from models.answer import InterviewAnswer
        
        db = SessionLocal()
        answers = db.query(InterviewAnswer).filter(
            InterviewAnswer.session_id == session_id
        ).all()
        db.close()
        
        if not answers:
            log_test(9, "Audio Transcription", "FAIL",
                    "No answers found", f"session={session_id}")
        else:
            transcription = getattr(answers[0], "transcription", None)
            if not transcription or len(str(transcription).strip()) == 0:
                log_test(9, "Audio Transcription", "FAIL",
                        "Transcription empty", None)
            else:
                log_test(9, "Audio Transcription", "PASS",
                        f"Transcription recorded", None)
    except Exception as e:
        log_test(9, "Audio Transcription", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# TEST 10: FORGOT PASSWORD
# ============================================================================

try:
    email_for_reset = f"reset{int(time.time())}@test.com"
    password = "ResetTest123!"
    
    # Register
    r_reg = requests.post(f"{BASE_URL}/register", json={
        "name": "Reset User",
        "email": email_for_reset,
        "password": password
    })
    
    if r_reg.status_code not in [200, 201]:
        log_test(10, "Forgot Password", "FAIL",
                f"Setup failed: {r_reg.status_code}", r_reg.text)
    else:
        # Request reset
        r_forgot = requests.post(f"{BASE_URL}/forgot-password", json={
            "email": email_for_reset
        })
        
        if r_forgot.status_code != 200:
            log_test(10, "Forgot Password", "FAIL",
                    f"Forgot password failed: {r_forgot.status_code}", r_forgot.text)
        else:
            token = r_forgot.json().get("reset_token")
            if not token:
                log_test(10, "Forgot Password", "FAIL",
                        "No reset token returned", r_forgot.json())
            else:
                # Reset password
                new_pass = "NewReset456!"
                r_reset = requests.post(f"{BASE_URL}/reset-password", json={
                    "token": token,
                    "new_password": new_pass
                })
                
                if r_reset.status_code != 200:
                    log_test(10, "Forgot Password", "FAIL",
                            f"Reset failed: {r_reset.status_code}", r_reset.text)
                else:
                    # Try login
                    r_login = requests.post(f"{BASE_URL}/login", json={
                        "email": email_for_reset,
                        "password": new_pass
                    })
                    
                    if r_login.status_code != 200:
                        log_test(10, "Forgot Password", "FAIL",
                                f"Login with new password failed", r_login.text)
                    else:
                        log_test(10, "Forgot Password", "PASS",
                                "Password reset and login successful", None)
except Exception as e:
    log_test(10, "Forgot Password", "FAIL", "Exception", traceback.format_exc())

# ============================================================================
# FINAL REPORT
# ============================================================================

print("\n\n" + "="*70)
print("VALIDATION AUDIT - FINAL REPORT")
print("="*70)

passed = [t for t in TEST_RESULTS if t["status"] == "PASS"]
failed = [t for t in TEST_RESULTS if t["status"] == "FAIL"]
blocked = [t for t in TEST_RESULTS if t["status"] == "BLOCKED"]

print(f"\n[OK] PASSED: {len(passed)}/10")
print(f"[FAIL] FAILED: {len(failed)}/10")
print(f"[?] BLOCKED: {len(blocked)}/10")

if failed:
    print(f"\n[CRITICAL] ISSUES ({len(failed)}):")
    for result in failed:
        print(f"  TEST {result['test']}: {result['name']}")
        print(f"    → {result['details']}")
        if result['error']:
            print(f"    → ERROR: {result['error'][:150]}")

print("\n" + "="*70)
print("VERDICT")
print("="*70)

if len(passed) == 10:
    verdict = "[OK] STABLE"
elif len(passed) >= 7:
    verdict = "[WARN] PARTIALLY STABLE"
else:
    verdict = "[FAIL] UNSTABLE"

print(f"Status: {verdict}")
print(f"Pass Rate: {len(passed)}/10 ({int(len(passed)*10)}%)")

# Save report
with open("validation_report.json", "w") as f:
    json.dump(TEST_RESULTS, f, indent=2)
print(f"\nReport saved: validation_report.json")

print("\n" + "="*70)
