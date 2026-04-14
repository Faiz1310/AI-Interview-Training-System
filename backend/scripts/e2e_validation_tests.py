"""
END-TO-END SYSTEM VALIDATION
Act as a real user tester - validate every flow step by step
"""
import requests
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Configuration
BACKEND_URL = "http://127.0.0.1:8000"
DB_PATH = Path(__file__).parent / "interview_prep.db"

# Test user credentials
TEST_USER = {
    "name": "Test User",
    "email": f"test_user_{datetime.now().timestamp()}@test.com",
    "password": "TestPassword123!"
}

# Global state
JWT_TOKEN = None
USER_ID = None
RESUME_ID = None
SESSION_ID = None

def print_test_header(test_num, test_name):
    """Print test header"""
    print(f"\n{'='*70}")
    print(f"TEST {test_num}: {test_name}")
    print(f"{'='*70}")

def print_status(status, message):
    """Print status"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {message}")

def print_error(title, message):
    """Print error"""
    print(f"\n❌ ERROR: {title}")
    print(f"   {message}")

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(str(DB_PATH))

def query_db(sql, params=None):
    """Execute database query"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print_error("Database Query Failed", str(e))
        return None

# ─── TEST 1: AUTH SYSTEM ─────────────────────────────────────────────────
def test_auth_system():
    """TEST 1: Register, Login, JWT validation"""
    global JWT_TOKEN, USER_ID
    
    print_test_header(1, "AUTH SYSTEM (Register → Login → JWT)")
    
    # Step 1.1: Register
    print("\n[1.1] Registering user...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/register",
            json={
                "name": TEST_USER["name"],
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        
        if response.status_code != 200:
            print_error("Registration Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        reg_data = response.json()
        print_status(True, f"Registration successful - User ID: {reg_data.get('user_id')}")
        USER_ID = reg_data.get("user_id")
        
    except Exception as e:
        print_error("Registration Exception", str(e))
        return False
    
    # Step 1.2: Login
    print("\n[1.2] Logging in...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        
        if response.status_code != 200:
            print_error("Login Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        login_data = response.json()
        JWT_TOKEN = login_data.get("access_token")
        
        if not JWT_TOKEN:
            print_error("Login Failed", "No JWT token in response")
            return False
        
        print_status(True, f"Login successful - JWT obtained")
        
    except Exception as e:
        print_error("Login Exception", str(e))
        return False
    
    # Step 1.3: Verify JWT works
    print("\n[1.3] Verifying JWT token...")
    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        response = requests.get(
            f"{BACKEND_URL}/me",
            headers=headers
        )
        
        if response.status_code != 200:
            print_error("JWT Verification Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        user_data = response.json()
        print_status(True, f"JWT valid - User: {user_data.get('email')}")
        
    except Exception as e:
        print_error("JWT Verification Exception", str(e))
        return False
    
    # Step 1.4: Check database
    print("\n[1.4] Checking database...")
    users = query_db("SELECT id, email, is_active FROM users WHERE email = ?", (TEST_USER["email"],))
    if users and users[0][2]:  # is_active
        print_status(True, f"User in DB: {users[0]}")
    else:
        print_error("Database Check Failed", "User not found or not active")
        return False
    
    print_status(True, "✓ TEST 1 PASSED")
    return True

# ─── TEST 2: RESUME UPLOAD ─────────────────────────────────────────────
def test_resume_upload():
    """TEST 2: Upload resume, check storage"""
    global RESUME_ID
    
    print_test_header(2, "RESUME UPLOAD (Upload → Store → Verify)")
    
    if not JWT_TOKEN:
        print_error("Precondition Failed", "JWT token not available (TEST 1 must pass first)")
        return False
    
    # Step 2.1: Create test resume
    print("\n[2.1] Creating test resume...")
    resume_text = """
    John Doe
    Software Engineer
    
    EXPERIENCE:
    - 5 years Python development
    - Built REST APIs
    - Machine learning projects
    
    SKILLS:
    - Python, JavaScript, React
    - FastAPI, Django
    - SQL, MongoDB
    - Docker, Kubernetes
    """
    
    jd_text = """
    Software Engineer Position
    
    Requirements:
    - 3+ years Python experience
    - REST API development
    - Microservices architecture
    - CI/CD pipelines
    """
    
    print_status(True, "Test resume created")
    
    # Step 2.2: Upload resume
    print("\n[2.2] Uploading resume...")
    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        files = {
            "resume_file": ("test_resume.txt", resume_text),
            "jd_file": ("test_jd.txt", jd_text)
        }
        data = {
            "job_role": "Senior Python Developer"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/upload_resume",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code != 200:
            print_error("Resume Upload Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        upload_data = response.json()
        RESUME_ID = upload_data.get("id")
        
        if not RESUME_ID:
            print_error("Resume Upload Failed", "No resume ID returned")
            return False
        
        print_status(True, f"Resume uploaded - ID: {RESUME_ID}")
        
    except Exception as e:
        print_error("Resume Upload Exception", str(e))
        return False
    
    # Step 2.3: Verify database
    print("\n[2.3] Verifying resume in database...")
    resumes = query_db("SELECT id, user_id, job_role, resume_text FROM resumes WHERE id = ?", (RESUME_ID,))
    
    if not resumes:
        print_error("Database Verification Failed", "Resume not found in DB")
        return False
    
    resume_data = resumes[0]
    if not resume_data[2] or not resume_data[3]:
        print_error("Database Verification Failed", "Resume missing job_role or resume_text")
        return False
    
    print_status(True, f"Resume in DB: ID={resume_data[0]}, Job Role={resume_data[2]}")
    
    print_status(True, "✓ TEST 2 PASSED")
    return True

# ─── TEST 3: START INTERVIEW ────────────────────────────────────────────
def test_start_interview():
    """TEST 3: Start interview session, generate first question"""
    global SESSION_ID
    
    print_test_header(3, "START INTERVIEW (Create Session → Generate Question)")
    
    if not JWT_TOKEN or not RESUME_ID:
        print_error("Precondition Failed", "JWT or Resume ID not available")
        return False
    
    # Step 3.1: Start session
    print("\n[3.1] Starting interview session...")
    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        response = requests.post(
            f"{BACKEND_URL}/start_session",
            headers=headers,
            json={"resume_id": RESUME_ID}
        )
        
        if response.status_code != 200:
            print_error("Session Start Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        session_data = response.json()
        SESSION_ID = session_data.get("session_id")
        
        if not SESSION_ID:
            print_error("Session Start Failed", "No session ID in response")
            return False
        
        print_status(True, f"Session started - ID: {SESSION_ID}")
        
    except Exception as e:
        print_error("Session Start Exception", str(e))
        return False
    
    # Step 3.2: Get first question
    print("\n[3.2] Fetching first question...")
    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        response = requests.get(
            f"{BACKEND_URL}/session/{SESSION_ID}/next_question",
            headers=headers
        )
        
        if response.status_code != 200:
            print_error("Get Question Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        question_data = response.json()
        question_text = question_data.get("question_text")
        question_type = question_data.get("question_type")
        
        if not question_text:
            print_error("Get Question Failed", "Question text is empty")
            return False
        
        if len(question_text.strip()) < 10:
            print_error("Get Question Failed", f"Question too short: '{question_text}'")
            return False
        
        print_status(True, f"Question generated - Type: {question_type}")
        print(f"   Q: {question_text[:80]}...")
        
    except Exception as e:
        print_error("Get Question Exception", str(e))
        return False
    
    # Step 3.3: Verify database
    print("\n[3.3] Verifying session in database...")
    sessions = query_db("SELECT id, user_id, status FROM interview_sessions WHERE id = ?", (SESSION_ID,))
    
    if not sessions:
        print_error("Database Verification Failed", "Session not found in DB")
        return False
    
    session_row = sessions[0]
    if session_row[2] != "in_progress":
        print_error("Database Verification Failed", f"Session status is '{session_row[2]}', expected 'in_progress'")
        return False
    
    print_status(True, f"Session in DB: ID={session_row[0]}, Status={session_row[2]}")
    
    print_status(True, "✓ TEST 3 PASSED")
    return True

# ─── TEST 4: ANSWER SUBMISSION & EVALUATION ──────────────────────────────
def test_answer_flow():
    """TEST 4: Submit answer, evaluate, get next question"""
    
    print_test_header(4, "ANSWER SUBMISSION & EVALUATION")
    
    if not JWT_TOKEN or not SESSION_ID:
        print_error("Precondition Failed", "JWT or Session ID not available")
        return False
    
    # Step 4.1: Submit answer
    print("\n[4.1] Submitting answer...")
    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        response = requests.post(
            f"{BACKEND_URL}/submit_answer",
            headers=headers,
            json={
                "session_id": SESSION_ID,
                "question_index": 1,
                "answer": "I have 5 years of Python experience building REST APIs and microservices..."
            }
        )
        
        if response.status_code not in [200, 201]:
            print_error("Answer Submission Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        answer_data = response.json()
        print_status(True, f"Answer submitted - ID: {answer_data.get('answer_id')}")
        
    except Exception as e:
        print_error("Answer Submission Exception", str(e))
        return False
    
    # Step 4.2: Check evaluation
    print("\n[4.2] Checking answer evaluation...")
    try:
        correctness = answer_data.get("correctness")
        clarity = answer_data.get("clarity")
        confidence = answer_data.get("confidence")
        
        # Check if scores are reasonable
        issues = []
        if correctness is None or not (0 <= correctness <= 1):
            issues.append(f"Correctness invalid: {correctness}")
        if clarity is None or not (0 <= clarity <= 1):
            issues.append(f"Clarity invalid: {clarity}")
        if confidence is None or not (0 <= confidence <= 1):
            issues.append(f"Confidence invalid: {confidence}")
        
        if issues:
            print_error("Evaluation Invalid", "; ".join(issues))
            return False
        
        print_status(True, f"Scores - Correctness: {correctness:.2f}, Clarity: {clarity:.2f}, Confidence: {confidence:.2f}")
        
    except Exception as e:
        print_error("Evaluation Check Exception", str(e))
        return False
    
    # Step 4.3: Check answer in database
    print("\n[4.3] Verifying answer in database...")
    answers = query_db("SELECT id, answer, correctness FROM interview_answers WHERE session_id = ?", (SESSION_ID,))
    
    if not answers:
        print_error("Database Verification Failed", "Answer not found in DB")
        return False
    
    print_status(True, f"Answer in DB: {len(answers)} answer(s) recorded")
    
    print_status(True, "✓ TEST 4 PASSED")
    return True

# ─── TEST 5: SESSION COMPLETION ────────────────────────────────────────
def test_session_completion():
    """TEST 5: Complete interview session"""
    
    print_test_header(5, "SESSION COMPLETION")
    
    if not JWT_TOKEN or not SESSION_ID:
        print_error("Precondition Failed", "JWT or Session ID not available")
        return False
    
    # Step 5.1: Complete session
    print("\n[5.1] Completing interview session...")
    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        response = requests.post(
            f"{BACKEND_URL}/end_session",
            headers=headers,
            json={"session_id": SESSION_ID}
        )
        
        if response.status_code not in [200, 201]:
            print_error("Session Completion Failed", f"Status {response.status_code}: {response.text}")
            return False
        
        complete_data = response.json()
        print_status(True, "Session marked as completed")
        
    except Exception as e:
        print_error("Session Completion Exception", str(e))
        return False
    
    # Step 5.2: Verify session status
    print("\n[5.2] Verifying session status...")
    sessions = query_db("SELECT status, overall_score FROM interview_sessions WHERE id = ?", (SESSION_ID,))
    
    if not sessions:
        print_error("Verification Failed", "Session not found")
        return False
    
    status = sessions[0][0]
    score = sessions[0][1]
    
    if status != "completed":
        print_error("Verification Failed", f"Status is '{status}', expected 'completed'")
        return False
    
    if score is None:
        print_error("Verification Failed", "Overall score is NULL")
        return False
    
    print_status(True, f"Session completed - Status: {status}, Score: {score}")
    
    print_status(True, "✓ TEST 5 PASSED")
    return True

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 AI INTERVIEW SYSTEM - END-TO-END VALIDATION")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("AUTH SYSTEM", test_auth_system()))
    results.append(("RESUME UPLOAD", test_resume_upload()))
    results.append(("START INTERVIEW", test_start_interview()))
    results.append(("ANSWER SUBMISSION", test_answer_flow()))
    results.append(("SESSION COMPLETION", test_session_completion()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    print("="*70)
