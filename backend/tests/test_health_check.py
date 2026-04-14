#!/usr/bin/env python
"""Quick test to verify backend components work"""

print("=" * 60)
print("SYSTEM HEALTH CHECK - LetsTrain.ai Backend")
print("=" * 60)

# Test 1: Import feedback service
try:
    from services.feedback_service import FeedbackService, SCORING_CONFIG
    print("✓ FeedbackService imported successfully")
    print(f"✓ Scoring Config Weights:")
    print(f"  - Correctness: {SCORING_CONFIG['weights']['correctness']['weight']} (50%)")
    print(f"  - Clarity: {SCORING_CONFIG['weights']['clarity']['weight']} (30%)")
    print(f"  - Confidence: {SCORING_CONFIG['weights']['confidence']['weight']} (20%)")
except Exception as e:
    print(f"✗ Error importing FeedbackService: {e}")
    exit(1)

# Test 2: Import models
try:
    from models.session import InterviewSession
    from models.answer import InterviewAnswer
    from models.behavior_issue import BehaviorIssue
    print("✓ All database models imported successfully")
except Exception as e:
    print(f"✗ Error importing models: {e}")
    exit(1)

# Test 3: Import routes
try:
    from routes.feedback_routes import router as feedback_router
    print("✓ Feedback routes imported successfully")
except Exception as e:
    print(f"✗ Error importing routes: {e}")
    exit(1)

# Test 4: Verify database connection
try:
    from database import init_db, get_db
    init_db()
    print("✓ Database initialized successfully")
except Exception as e:
    print(f"✗ Error initializing database: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL BACKEND COMPONENTS HEALTHY")
print("=" * 60)
print("\nBranding: LetsTrain.ai")
print("Feature: AI Interview Training System")
print("Status: Ready for testing")
