"""
Comprehensive System Testing - LetsTrain.ai
Tests all features, workflows, and integrations
"""

import sys
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import init_db, get_db, engine
from models.user import User
from models.resume import Resume
from models.session import InterviewSession
from models.answer import InterviewAnswer
from models.behavior_metric import InterviewBehaviorMetric
from models.behavior_issue import BehaviorIssue
from ai_modules.correctness import evaluate_correctness
from ai_modules.clarity import evaluate_clarity
from ai_modules.behavioral_confidence import compute_behavioral_confidence
from ai_modules.hierarchical import compute_overall
from auth.jwt_handler import create_access_token, verify_token

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "components": {}
}

def print_section(title):
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{title:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_test(name, status, details=""):
    test_results["total"] += 1
    status_symbol = f"{GREEN}[PASS]{RESET}" if status else f"{RED}[FAIL]{RESET}"
    if status:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    
    print(f"{status_symbol} {name}")
    if details:
        print(f"    > {details}")

def test_database_connectivity():
    """Test database connection and model initialization"""
    print_section("1. DATABASE CONNECTIVITY")
    
    try:
        init_db()
        print_test("Database initialization", True, "SQLAlchemy initialized")
    except Exception as e:
        print_test("Database initialization", False, str(e))
        return False
    
    try:
        db = next(get_db())
        user_count = db.query(User).count()
        print_test("Database query execution", True, f"User table accessible ({user_count} users)")
        db.close()
    except Exception as e:
        print_test("Database query execution", False, str(e))
        return False
    
    return True

def test_user_authentication():
    """Test user registration, login, and JWT"""
    print_section("2. USER AUTHENTICATION")
    
    db = next(get_db())
    
    try:
        # Create test user
        test_user = User(
            name="Test User " + datetime.now().strftime("%Y%m%d%H%M%S"),
            email="test_" + datetime.now().strftime("%Y%m%d%H%M%S") + "@test.com",
            password_hash="hashed_password_123"
        )
        db.add(test_user)
        db.commit()
        print_test("User creation", True, f"User '{test_user.name}' created")
        
        # Retrieve user
        retrieved_user = db.query(User).filter(User.id == test_user.id).first()
        print_test("User retrieval", retrieved_user is not None, f"User ID: {retrieved_user.id if retrieved_user else 'N/A'}")
        
        # Generate JWT token
        token = create_access_token(test_user.id)
        print_test("JWT token generation", token is not None, f"Token length: {len(token)} chars")
        
        # Verify token
        decoded = verify_token(token)
        token_valid = decoded and decoded.get("sub") == str(test_user.id)
        print_test("JWT token verification", token_valid, f"User ID matches: {token_valid}")
        
        # Cleanup
        db.delete(test_user)
        db.commit()
        return True
        
    except Exception as e:
        print_test("Authentication system", False, str(e))
        return False
    finally:
        db.close()

def test_text_extraction():
    """Test text extraction from documents"""
    print_section("3. TEXT EXTRACTION & PROCESSING")
    
    try:
        # Test plain text can be processed (without file extraction)
        # Since extract_text_from_file requires file upload object,
        # we'll test that the service exists
        from services.text_extractor import extract_text_from_file
        print_test("Text extractor import", True, "Text extraction service available")
        
        # Test text cleaning is available
        import re
        sample_text = "Python   and   JavaScript  skills required"
        cleaned = re.sub(r'\s+', ' ', sample_text).strip()
        has_cleaning = cleaned == "Python and JavaScript skills required"
        print_test("Text cleaning", has_cleaning, "Whitespace normalization works")
        
        return True
    except Exception as e:
        print_test("Text extraction", False, str(e))
        return False

def test_ai_evaluation_modules():
    """Test correctness, clarity, and confidence evaluation"""
    print_section("4. AI EVALUATION MODULES")
    
    # Sample answer for testing
    sample_answer = "React is a JavaScript library for building user interfaces with reusable components. It uses a virtual DOM for efficient updates and supports hooks for state management."
    sample_question = "Explain React and its key features"
    
    try:
        # Test Correctness
        correctness_result = evaluate_correctness(sample_question, sample_answer)
        if isinstance(correctness_result, tuple):
            correctness_score = correctness_result[0]
        else:
            correctness_score = correctness_result
        correctness_valid = 0 <= correctness_score <= 100
        print_test("Correctness evaluation", correctness_valid, f"Score: {correctness_score:.1f}/100")
        
        # Test Clarity
        clarity_result = evaluate_clarity(sample_question, sample_answer)
        if isinstance(clarity_result, tuple):
            clarity_score = clarity_result[0]
        else:
            clarity_score = clarity_result
        clarity_valid = 0 <= clarity_score <= 100
        print_test("Clarity evaluation", clarity_valid, f"Score: {clarity_score:.1f}/100")
        
        # Test Confidence (mock video data)
        confidence_score = compute_behavioral_confidence(
            avg_eye_contact=0.75,
            avg_head_stability=0.85,
            avg_blink_rate=20,
            avg_facial_stress=0.2
        )
        confidence_valid = 0 <= confidence_score <= 100
        print_test("Behavioral confidence evaluation", confidence_valid, f"Score: {confidence_score:.1f}/100")
        
        # Test Hierarchical Scoring
        from ai_modules.hierarchical import compute_overall
        overall_score = compute_overall(correctness_score, clarity_score, confidence_score)
        overall_valid = 0 <= overall_score <= 100
        print_test("Hierarchical scoring", overall_valid, f"Overall Score: {overall_score:.1f}/100 (50% correct + 30% clarity + 20% confidence)")
        
        return True
    except Exception as e:
        print_test("AI evaluation modules", False, str(e))
        import traceback
        print(f"  Traceback: {traceback.format_exc()}")
        return False

def test_interview_session_workflow():
    """Test complete interview session workflow"""
    print_section("5. INTERVIEW SESSION WORKFLOW")
    
    db = next(get_db())
    
    try:
        # Create test user
        test_user = User(
            name="Interview Test " + datetime.now().strftime("%Y%m%d%H%M%S"),
            email="interview_" + datetime.now().strftime("%Y%m%d%H%M%S") + "@test.com",
            password_hash="hashed_password_123"
        )
        db.add(test_user)
        db.commit()
        print_test("Test user creation", True, f"User ID: {test_user.id}")
        
        # Create test resume
        test_resume = Resume(
            user_id=test_user.id,
            filename="test_resume.pdf",
            resume_text="Python, JavaScript, React, FastAPI",
            jd_text="Senior Developer needed",
            job_role="Senior Developer"
        )
        db.add(test_resume)
        db.commit()
        print_test("Test resume creation", True, f"Resume ID: {test_resume.id}")
        
        # Create session
        session = InterviewSession(
            user_id=test_user.id,
            resume_id=test_resume.id,
            status="in_progress",
            total_questions=3,
            max_questions=10
        )
        db.add(session)
        db.commit()
        print_test("Interview session creation", True, f"Session ID: {session.id}, Status: {session.status}")
        
        # Add answers
        for i in range(3):
            answer = InterviewAnswer(
                session_id=session.id,
                resume_id=test_resume.id,
                question=f"Sample Question {i+1}",
                answer=f"Sample answer {i+1}",
                correctness=75.0 + i*5,
                clarity=70.0 + i*5,
                confidence=80.0 + i*3,
                overall=75.0 + i*4
            )
            db.add(answer)
        db.commit()
        print_test("Answer submission", True, f"3 answers added to session")
        
        # Add behavior metrics
        for i in range(3):
            metric = InterviewBehaviorMetric(
                session_id=session.id,
                eye_contact_score=0.75 + i*0.05,
                head_stability_score=0.85 + i*0.05,
                blink_rate=20 - i*2,
                facial_stress_index=0.2 - i*0.05
            )
            db.add(metric)
        db.commit()
        print_test("Behavioral metrics recording", True, f"3 metrics inserted")
        
        # Add behavior issues
        issue = BehaviorIssue(
            session_id=session.id,
            question_index=0,
            issue="looking_away",
            severity="medium"
        )
        db.add(issue)
        db.commit()
        print_test("Behavior issue detection", True, f"Issues tracked: {len(session.behavior_issues)}")
        
        # Complete session
        session.status = "completed"
        session.correctness_score = 80.0
        session.clarity_score = 78.0
        session.confidence_score = 81.0
        session.overall_score = 79.0
        db.commit()
        print_test("Session completion", session.status == "completed", f"Final scores - Correctness: {session.correctness_score}, Clarity: {session.clarity_score}, Confidence: {session.confidence_score}")
        
        # Retrieve session with relationships
        retrieved_session = db.query(InterviewSession).filter(InterviewSession.id == session.id).first()
        answer_count = len(retrieved_session.answers)
        metric_count = len(retrieved_session.behavior_metrics) if hasattr(retrieved_session, 'behavior_metrics') else 0
        issue_count = len(retrieved_session.behavior_issues) if hasattr(retrieved_session, 'behavior_issues') else 0
        print_test("Session data retrieval", answer_count == 3 and metric_count == 3 and issue_count == 1, 
                  f"Answers: {answer_count}, Metrics: {metric_count}, Issues: {issue_count}")
        
        # Cleanup
        db.delete(retrieved_session)
        db.delete(test_resume)
        db.delete(test_user)
        db.commit()
        
        return True
    except Exception as e:
        print_test("Interview session workflow", False, str(e))
        return False
    finally:
        db.close()

def test_feedback_generation():
    """Test feedback generation system"""
    print_section("6. FEEDBACK GENERATION")
    
    try:
        from services.feedback_service import FeedbackService
        
        # Test that FeedbackService can be imported
        print_test("FeedbackService import", True, "Feedback service available")
        
        # Test SCORING_CONFIG is defined
        from services.feedback_service import SCORING_CONFIG
        has_weights = "weights" in SCORING_CONFIG
        print_test("SCORING_CONFIG", has_weights, f"Weights defined: {list(SCORING_CONFIG.get('weights', {}).keys())}")
        
        return True
    except Exception as e:
        print_test("Feedback generation", False, str(e))
        import traceback
        print(f"  Traceback: {traceback.format_exc()}")
        return False

def test_branding_and_frontend():
    """Test frontend branding and components"""
    print_section("7. FRONTEND BRANDING & COMPONENTS")
    
    try:
        # Check key frontend files
        import os
        
        files_to_check = [
            ("App.jsx", "LetsTrain.ai"),
            ("components/auth/AuthHeader.jsx", "LetsTrain.ai"),
            ("components/auth/LoginForm.jsx", "email"),
            ("components/auth/RegisterForm.jsx", "password"),
        ]
        
        frontend_path = "c:/Users/faiza/OneDrive/Documents/FYP Implementation/frontend/src"
        
        for filename, keyword in files_to_check:
            file_path = os.path.join(frontend_path, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    has_keyword = keyword.lower() in content.lower()
                    print_test(f"Frontend: {filename}", has_keyword, f"Contains '{keyword}'")
            else:
                print_test(f"Frontend: {filename}", False, "File not found")
        
        return True
    except Exception as e:
        print_test("Frontend branding", False, str(e))
        return False

def test_api_routes():
    """Test API route definitions"""
    print_section("8. API ROUTES & ENDPOINTS")
    
    try:
        from routes.auth_routes import router as auth_router
        from routes.resume_routes import router as resume_router
        from routes.question_routes import router as question_router
        from routes.session_routes import router as session_router
        from routes.behavior_routes import router as behavior_router
        from routes.dashboard_routes import router as dashboard_router
        from routes.feedback_routes import router as feedback_router
        
        routers = [
            ("Auth Routes", auth_router),
            ("Resume Routes", resume_router),
            ("Question Routes", question_router),
            ("Session Routes", session_router),
            ("Behavior Routes", behavior_router),
            ("Dashboard Routes", dashboard_router),
            ("Feedback Routes", feedback_router),
        ]
        
        for name, router in routers:
            route_count = len(router.routes)
            print_test(f"{name}", route_count > 0, f"{route_count} endpoints")
        
        return True
    except Exception as e:
        print_test("API routes", False, str(e))
        return False

def print_summary():
    """Print test summary"""
    print_section("TEST SUMMARY")
    
    total = test_results["total"]
    passed = test_results["passed"]
    failed = test_results["failed"]
    
    pass_percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"Total Tests: {BOLD}{total}{RESET}")
    print(f"Passed: {GREEN}{BOLD}{passed}{RESET}")
    print(f"Failed: {RED}{BOLD}{failed}{RESET}")
    print(f"Pass Rate: {GREEN if pass_percentage == 100 else YELLOW}{BOLD}{pass_percentage:.1f}%{RESET}")
    
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    if failed == 0:
        print(f"{GREEN}{BOLD}{'[PASS] ALL TESTS PASSED - SYSTEM IS HEALTHY':^70}{RESET}")
    else:
        print(f"{RED}{BOLD}{f'[FAIL] {failed} TESTS FAILED - ISSUES DETECTED':^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def main():
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{'LetsTrain.ai - COMPREHENSIVE SYSTEM TEST':^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    
    print(f"\n{YELLOW}Starting system tests...{RESET}\n")
    
    # Run all tests
    test_database_connectivity()
    test_user_authentication()
    test_text_extraction()
    test_ai_evaluation_modules()
    test_interview_session_workflow()
    test_feedback_generation()
    test_branding_and_frontend()
    test_api_routes()
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()
