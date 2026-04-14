#!/usr/bin/env python3
"""
FINAL SYSTEM VALIDATION + PROOF MODE
Complete end-to-end testing with real HTTP requests.
All results are evidenced, not assumed.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []

def test(num, name, passed, status, response_sample=None):
    """Record test result with evidence"""
    result = {
        "test": num,
        "name": name,
        "passed": passed,
        "status": status,
        "response_sample": response_sample,
        "timestamp": datetime.now().isoformat()
    }
    RESULTS.append(result)
    
    symbol = "[PASS]" if passed else "[FAIL]"
    print(f"\n{symbol} TEST {num}: {name}")
    print(f"     Status: {status}")
    if response_sample:
        print(f"     Response: {response_sample}")

print("\n" + "="*70)
print("FINAL SYSTEM VALIDATION - VIVA PANEL MODE")
print("="*70)
print(f"Time: {datetime.now().isoformat()}")
print(f"Backend: {BASE_URL}")

# Verify backend is accessible
print("\n[*] Checking backend availability...")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"[OK] Backend responding: {r.status_code}")
except Exception as e:
    print(f"[FAIL] Backend unreachable: {e}")
    print("[!] Stopping validation - backend not running")
    exit(1)

# ============================================================================
# TEST 1: AUTH SYSTEM
# ============================================================================

test_email = f"viva_user_{int(time.time())}@test.com"
test_password = "VivaPa55w0rd!"
test_token = None
test_user_id = None

try:
    # Register
    payload = {"name": "VIVA User", "email": test_email, "password": test_password}
    r_reg = requests.post(f"{BASE_URL}/register", json=payload)
    
    if r_reg.status_code != 200:
        test(1, "Auth System", False, 
             f"Register failed: {r_reg.status_code}", 
             f"{r_reg.text[:100]}")
    else:
        test_user_id = r_reg.json().get("id")
        
        # Login
        r_login = requests.post(f"{BASE_URL}/login", 
                               json={"email": test_email, "password": test_password})
        
        if r_login.status_code != 200:
            test(1, "Auth System", False, 
                 f"Login failed: {r_login.status_code}",
                 f"{r_login.text[:100]}")
        else:
            test_token = r_login.json().get("access_token")
            
            if not test_token:
                test(1, "Auth System", False,
                    "No token in response",
                    f"{r_login.json()}")
            else:
                # Verify token works
                headers = {"Authorization": f"Bearer {test_token}"}
                r_me = requests.get(f"{BASE_URL}/me", headers=headers)
                
                if r_me.status_code != 200:
                    test(1, "Auth System", False,
                        f"Token validation failed: {r_me.status_code}",
                        f"{r_me.text[:100]}")
                else:
                    test(1, "Auth System", True,
                        f"Register->Login->Token verified",
                        f"User ID: {test_user_id}, Email: {test_email}")
except Exception as e:
    test(1, "Auth System", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 2: RESUME PIPELINE
# ============================================================================

test_resume_id = None

if not test_token:
    test(2, "Resume Pipeline", False, "Blocked: No auth token", None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Upload resume
        resume_text = "Alice Johnson\nSenior Python Engineer\n5+ years Python, FastAPI, AWS, Docker"
        jd_text = "Need Python dev with FastAPI"
        
        files = {
            "resume_file": ("resume.txt", resume_text),
            "jd_file": ("jd.txt", jd_text)
        }
        data = {"job_role": "Senior Backend Engineer"}
        
        r_upload = requests.post(f"{BASE_URL}/upload_resume", 
                                headers=headers, files=files, data=data)
        
        if r_upload.status_code != 200:
            test(2, "Resume Pipeline", False,
                f"Upload failed: {r_upload.status_code}",
                f"{r_upload.text[:100]}")
        else:
            test_resume_id = r_upload.json().get("id")
            
            if not test_resume_id:
                test(2, "Resume Pipeline", False,
                    "No resume ID returned",
                    f"{r_upload.json()}")
            else:
                test(2, "Resume Pipeline", True,
                    "Resume uploaded and stored",
                    f"Resume ID: {test_resume_id}")
    except Exception as e:
        test(2, "Resume Pipeline", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 3: INTERVIEW START
# ============================================================================

test_session_id = None

if not test_token or not test_resume_id:
    test(3, "Interview Start", False, "Blocked: Missing token or resume", None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        r_start = requests.post(f"{BASE_URL}/start_session",
                               headers=headers,
                               json={
                                   "resume_id": test_resume_id,
                                   "total_questions": 5,
                                   "difficulty_level": 2
                               })
        
        if r_start.status_code != 200:
            test(3, "Interview Start", False,
                f"Start session failed: {r_start.status_code}",
                f"{r_start.text[:100]}")
        else:
            session_data = r_start.json()
            test_session_id = session_data.get("session_id")
            
            if not test_session_id:
                test(3, "Interview Start", False,
                    "No session_id in response",
                    f"{session_data}")
            else:
                test(3, "Interview Start", True,
                    "Session created successfully",
                    f"Session ID: {test_session_id}")
    except Exception as e:
        test(3, "Interview Start", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 4: QUESTION FLOW
# ============================================================================

if not test_token or not test_session_id:
    test(4, "Question Flow", False, "Blocked: Missing session", None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Get first question
        r_q1 = requests.get(f"{BASE_URL}/session/{test_session_id}/next_question",
                           headers=headers)
        
        if r_q1.status_code != 200:
            test(4, "Question Flow", False,
                f"Get Q1 failed: {r_q1.status_code}",
                f"{r_q1.text[:100]}")
        else:
            q1 = r_q1.json()
            q1_data = q1.get("next_question", {})
            q1_text = q1_data.get("question_text", "")
            q1_id = q1_data.get("question_id") or q1_data.get("topic")
            
            if not q1_text or len(q1_text) < 15:
                test(4, "Question Flow", False,
                    "Question empty or too short",
                    f"Q1: {q1_text[:50]}")
            else:
                # Submit answer
                r_ans = requests.post(f"{BASE_URL}/submit_answer",
                                     headers=headers,
                                     json={
                                         "session_id": test_session_id,
                                         "question": q1_text,
                                         "answer": "I have strong experience with system design and microservices."
                                     })
                
                if r_ans.status_code != 200:
                    test(4, "Question Flow", False,
                        f"Submit answer failed: {r_ans.status_code}",
                        f"{r_ans.text[:100]}")
                else:
                    test(4, "Question Flow", True,
                        "Question retrieved and answered",
                        f"Q1: {q1_text[:60]}...")
    except Exception as e:
        test(4, "Question Flow", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 5: SESSION COMPLETION
# ============================================================================

if not test_token or not test_session_id:
    test(5, "Session Completion", False, "Blocked: Missing session", None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        r_complete = requests.post(f"{BASE_URL}/end_session",
                                  headers=headers,
                                  json={"session_id": test_session_id})
        
        if r_complete.status_code != 200:
            test(5, "Session Completion", False,
                f"Complete failed: {r_complete.status_code}",
                f"{r_complete.text[:100]}")
        else:
            test(5, "Session Completion", True,
                "Session marked as completed",
                f"{r_complete.json()}")
    except Exception as e:
        test(5, "Session Completion", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 6: FEEDBACK SYSTEM
# ============================================================================

if not test_token or not test_session_id:
    test(6, "Feedback System", False, "Blocked: Missing session", None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        r_feedback = requests.get(f"{BASE_URL}/session/{test_session_id}/feedback",
                                 headers=headers)
        
        if r_feedback.status_code != 200:
            test(6, "Feedback System", False,
                f"Fetch feedback failed: {r_feedback.status_code}",
                f"{r_feedback.text[:100]}")
        else:
            feedback = r_feedback.json()
            required = ["overall_score", "score_breakdown", "strengths", "weaknesses"]
            missing = [k for k in required if k not in feedback or feedback[k] is None]
            
            if missing:
                test(6, "Feedback System", False,
                    f"Missing fields: {missing}",
                    f"{json.dumps(feedback)[:100]}")
            else:
                test(6, "Feedback System", True,
                    "Feedback complete with all metrics",
                    f"Score: {feedback.get('overall_score')}, Breakdown: {feedback.get('score_breakdown')}")
    except Exception as e:
        test(6, "Feedback System", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 7: DASHBOARD & SOFT DELETE
# ============================================================================

if not test_token:
    test(7, "Dashboard & Soft Delete", False, "Blocked: No token", None)
else:
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Get sessions
        r_list = requests.get(f"{BASE_URL}/sessions", headers=headers)
        
        if r_list.status_code != 200:
            test(7, "Dashboard & Soft Delete", False,
                f"List sessions failed: {r_list.status_code}",
                f"{r_list.text[:100]}")
        else:
            sessions = r_list.json() if isinstance(r_list.json(), list) else []
            before_count = len(sessions)
            
            if test_session_id and before_count > 0:
                # Delete
                r_del = requests.delete(f"{BASE_URL}/session/{test_session_id}",
                                       headers=headers)
                
                if r_del.status_code != 200:
                    test(7, "Dashboard & Soft Delete", False,
                        f"Delete failed: {r_del.status_code}",
                        f"{r_del.text[:100]}")
                else:
                    time.sleep(0.5)
                    
                    # Check hidden
                    r_after = requests.get(f"{BASE_URL}/sessions", headers=headers)
                    after_count = len(r_after.json()) if isinstance(r_after.json(), list) else 0
                    
                    if after_count >= before_count:
                        test(7, "Dashboard & Soft Delete", False,
                            "Session not hidden after delete",
                            f"Before: {before_count}, After: {after_count}")
                    else:
                        test(7, "Dashboard & Soft Delete", True,
                            "Soft delete works (session hidden)",
                            f"Sessions: {before_count} -> {after_count}")
            else:
                test(7, "Dashboard & Soft Delete", False,
                    "No sessions to test delete",
                    None)
    except Exception as e:
        test(7, "Dashboard & Soft Delete", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 8: BEHAVIOR METRICS
# ============================================================================

if not test_session_id:
    test(8, "Behavior Metrics", False, "Blocked: No session", None)
else:
    try:
        from database import SessionLocal
        from models.behavior_metric import InterviewBehaviorMetric
        
        db = SessionLocal()
        metrics = db.query(InterviewBehaviorMetric).filter(
            InterviewBehaviorMetric.session_id == test_session_id
        ).all()
        db.close()
        
        if not metrics:
            test(8, "Behavior Metrics", False,
                "No behavior metrics found",
                f"Session: {test_session_id}")
        else:
            m = metrics[0]
            attention = getattr(m, "attention_score", None)
            
            if attention is None:
                test(8, "Behavior Metrics", False,
                    "attention_score is None",
                    None)
            elif not (0 <= attention <= 100):
                test(8, "Behavior Metrics", False,
                    f"attention_score out of range: {attention}",
                    None)
            else:
                test(8, "Behavior Metrics", True,
                    "Behavior metrics valid",
                    f"attention_score: {attention}")
    except Exception as e:
        test(8, "Behavior Metrics", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 9: AUDIO TRANSCRIPTION
# ============================================================================

if not test_session_id:
    test(9, "Audio Transcription", False, "Blocked: No session", None)
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
            test(9, "Audio Transcription", False,
                "No answers found",
                None)
        else:
            transcription = getattr(answers[0], "transcription", None)
            
            if not transcription or len(str(transcription).strip()) == 0:
                test(9, "Audio Transcription", False,
                    "Transcription empty",
                    None)
            else:
                test(9, "Audio Transcription", True,
                    "Transcription recorded",
                    f"{str(transcription)[:60]}...")
    except Exception as e:
        test(9, "Audio Transcription", False, f"Exception: {str(e)}", None)

# ============================================================================
# TEST 10: FORGOT PASSWORD
# ============================================================================

try:
    reset_email = f"reset_{int(time.time())}@test.com"
    reset_pw = "ResetPa55!"
    
    # Register user for reset
    r_reg = requests.post(f"{BASE_URL}/register",
                         json={"name": "Reset User", "email": reset_email, "password": reset_pw})
    
    if r_reg.status_code not in [200, 201]:
        test(10, "Forgot Password", False,
            f"Setup failed: {r_reg.status_code}",
            None)
    else:
        # Request reset
        r_forgot = requests.post(f"{BASE_URL}/forgot-password",
                                json={"email": reset_email})
        
        if r_forgot.status_code != 200:
            test(10, "Forgot Password", False,
                f"Forgot password failed: {r_forgot.status_code}",
                f"{r_forgot.text[:100]}")
        else:
            token = r_forgot.json().get("reset_token")
            
            if not token:
                test(10, "Forgot Password", False,
                    "No reset token returned",
                    f"{r_forgot.json()}")
            else:
                # Reset password
                new_pw = "NewPa55word!"
                r_reset = requests.post(f"{BASE_URL}/reset-password",
                                       json={"token": token, "new_password": new_pw})
                
                if r_reset.status_code != 200:
                    test(10, "Forgot Password", False,
                        f"Reset failed: {r_reset.status_code}",
                        f"{r_reset.text[:100]}")
                else:
                    # Login with new password
                    r_login = requests.post(f"{BASE_URL}/login",
                                           json={"email": reset_email, "password": new_pw})
                    
                    if r_login.status_code != 200:
                        test(10, "Forgot Password", False,
                            f"Login with new password failed",
                            f"{r_login.text[:100]}")
                    else:
                        test(10, "Forgot Password", True,
                            "Password reset and login successful",
                            f"Email: {reset_email}")
except Exception as e:
    test(10, "Forgot Password", False, f"Exception: {str(e)}", None)

# ============================================================================
# FINAL REPORT
# ============================================================================

print("\n\n" + "="*70)
print("FINAL VALIDATION REPORT")
print("="*70)

passed = [t for t in RESULTS if t["passed"]]
failed = [t for t in RESULTS if not t["passed"]]

print(f"\n[PASS] {len(passed)}/10 tests passed")
print(f"[FAIL] {len(failed)}/10 tests failed")

if failed:
    print(f"\n[CRITICAL] FAILING TESTS:")
    for f in failed:
        print(f"  TEST {f['test']}: {f['name']}")
        print(f"    → {f['status']}")

print("\n" + "="*70)

if len(passed) == 10:
    verdict = "[OK] STABLE - ALL TESTS PASS"
elif len(passed) >= 7:
    verdict = "[WARN] PARTIALLY STABLE - {failed} failures".format(failed=len(failed))
else:
    verdict = "[FAIL] UNSTABLE - {failed}/10 failures".format(failed=len(failed))

print(f"VERDICT: {verdict}")
print("="*70 + "\n")

# Save results
with open("final_validation_results.json", "w") as f:
    json.dump(RESULTS, f, indent=2)

print("Results saved to: final_validation_results.json")
