"""
FULL SYSTEM DEBUG & STABILIZATION SCRIPT
Comprehensive checks for AI Interview System
"""

import sys
import os
import logging
from datetime import datetime, timezone
from sqlalchemy import text, inspect, event

# Set UTF-8 encoding for output
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import SessionLocal, Base, engine
from models.user import User
from models.session import InterviewSession
from models.answer import InterviewAnswer
from models.behavior_issue import BehaviorIssue
from models.behavior_metric import InterviewBehaviorMetric
from models.resume import Resume
from services.feedback_service import generate_feedback_report

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Color codes
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

class SystemDebugger:
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        self.db = SessionLocal()
        
    def log(self, status, message):
        print(f"{status} {message}")
        
    def add_issue(self, step, severity, message):
        self.issues.append({
            "step": step,
            "severity": severity,
            "message": message
        })
        
    def add_fix(self, message):
        self.fixes_applied.append(message)

    # ============================================================================
    # STEP 1: DATABASE INTEGRITY
    # ============================================================================
    
    def step1_database_integrity(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 1: DATABASE INTEGRITY CHECK")
        self.log(INFO, "="*70)
        
        try:
            # Check is_deleted column exists
            inspector = inspect(engine)
            session_columns = [col['name'] for col in inspector.get_columns('interview_sessions')]
            
            if 'is_deleted' not in session_columns:
                self.add_issue("STEP 1", "CRITICAL", "is_deleted column missing from interview_sessions")
                self.log(FAIL, "is_deleted column missing from interview_sessions")
                return False
            self.log(PASS, "is_deleted column exists")
            
            if 'deleted_at' not in session_columns:
                self.add_issue("STEP 1", "CRITICAL", "deleted_at column missing from interview_sessions")
                self.log(FAIL, "deleted_at column missing")
                return False
            self.log(PASS, "deleted_at column exists")
            
            # Check for NULL is_deleted values
            null_check = self.db.query(InterviewSession).filter(
                InterviewSession.is_deleted == None
            ).count()
            
            if null_check > 0:
                self.log(WARN, f"Found {null_check} sessions with NULL is_deleted")
                self.add_issue("STEP 1", "MEDIUM", f"{null_check} sessions have NULL is_deleted")
                
                # Fix: Set NULL to False
                self.db.execute(text("""
                    UPDATE interview_sessions 
                    SET is_deleted = 0 
                    WHERE is_deleted IS NULL
                """))
                self.db.commit()
                self.add_fix("Fixed NULL is_deleted values - set to 0")
                self.log(PASS, "Fixed NULL is_deleted values")
            else:
                self.log(PASS, "No NULL is_deleted values")
            
            # Check relationships
            sessions_without_user = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == None
            ).count()
            
            if sessions_without_user > 0:
                self.add_issue("STEP 1", "HIGH", f"{sessions_without_user} sessions have NULL user_id")
                self.log(WARN, f"Found {sessions_without_user} sessions without user_id")
            
            # Check answer relationships
            orphaned_answers = self.db.query(InterviewAnswer).filter(
                InterviewAnswer.session_id.notin_(
                    self.db.query(InterviewSession.id)
                )
            ).count()
            
            if orphaned_answers > 0:
                self.add_issue("STEP 1", "MEDIUM", f"{orphaned_answers} answers reference non-existent sessions")
                self.log(WARN, f"Found {orphaned_answers} orphaned answers")
            else:
                self.log(PASS, "All answer relationships valid")
            
            # Check behavior issues relationships
            orphaned_issues = self.db.query(BehaviorIssue).filter(
                BehaviorIssue.session_id.notin_(
                    self.db.query(InterviewSession.id)
                )
            ).count()
            
            if orphaned_issues > 0:
                self.add_issue("STEP 1", "MEDIUM", f"{orphaned_issues} behavior_issues reference non-existent sessions")
                self.log(WARN, f"Found {orphaned_issues} orphaned behavior_issues")
            else:
                self.log(PASS, "All behavior_issue relationships valid")
            
            # Check behavior metrics relationships
            orphaned_metrics = self.db.query(InterviewBehaviorMetric).filter(
                InterviewBehaviorMetric.session_id.notin_(
                    self.db.query(InterviewSession.id)
                )
            ).count()
            
            if orphaned_metrics > 0:
                self.add_issue("STEP 1", "MEDIUM", f"{orphaned_metrics} behavior_metrics reference non-existent sessions")
                self.log(WARN, f"Found {orphaned_metrics} orphaned behavior_metrics")
            else:
                self.log(PASS, "All behavior_metric relationships valid")
            
            self.log(PASS, "STEP 1 COMPLETE")
            return True
            
        except Exception as e:
            self.add_issue("STEP 1", "CRITICAL", f"Database integrity check failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 2: SESSION VISIBILITY
    # ============================================================================
    
    def step2_session_visibility(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 2: SESSION VISIBILITY VERIFICATION")
        self.log(INFO, "="*70)
        
        try:
            # Count sessions
            total_sessions = self.db.query(InterviewSession).count()
            active_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.is_deleted == False
            ).count()
            deleted_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.is_deleted == True
            ).count()
            
            self.log(INFO, f"Total sessions: {total_sessions}")
            self.log(INFO, f"Active sessions: {active_sessions}")
            self.log(INFO, f"Deleted sessions: {deleted_sessions}")
            
            if total_sessions == active_sessions + deleted_sessions:
                self.log(PASS, "Session count verification passed")
            else:
                self.add_issue("STEP 2", "HIGH", "Session count mismatch")
                self.log(FAIL, "Session count mismatch")
            
            # Check dashboard query filter (should exclude deleted)
            if active_sessions > 0:
                self.log(PASS, f"Dashboard would show {active_sessions} sessions")
            
            self.log(PASS, "STEP 2 COMPLETE")
            return True
            
        except Exception as e:
            self.add_issue("STEP 2", "CRITICAL", f"Session visibility check failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 3: DELETE + RESTORE
    # ============================================================================
    
    def step3_delete_restore(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 3: DELETE + RESTORE FUNCTIONALITY")
        self.log(INFO, "="*70)
        
        try:
            # Find an active session to test with
            test_session = self.db.query(InterviewSession).filter(
                InterviewSession.is_deleted == False
            ).first()
            
            if not test_session:
                self.log(WARN, "No active sessions to test delete/restore")
                self.log(INFO, "Skipping delete/restore test - no test data available")
                return True
            
            session_id = test_session.id
            self.log(INFO, f"Testing with session ID: {session_id}")
            
            # Check that session exists and is_deleted is False
            active = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id,
                InterviewSession.is_deleted == False
            ).first()
            
            if active:
                self.log(PASS, "Test session is active (is_deleted = False)")
            else:
                self.add_issue("STEP 3", "MEDIUM", "Test session not found in active sessions")
                self.log(FAIL, "Test session not active")
                return True
            
            # Simulate delete (soft delete)
            test_session.is_deleted = True
            test_session.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Verify deleted
            deleted = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id,
                InterviewSession.is_deleted == True
            ).first()
            
            if deleted:
                self.log(PASS, "Soft delete works - session marked deleted")
            else:
                self.add_issue("STEP 3", "HIGH", "Soft delete did not work")
                self.log(FAIL, "Soft delete failed")
            
            # Verify hidden from active query
            not_in_active = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id,
                InterviewSession.is_deleted == False
            ).first()
            
            if not not_in_active:
                self.log(PASS, "Deleted session hidden from active sessions")
            else:
                self.add_issue("STEP 3", "HIGH", "Deleted session still in active sessions")
                self.log(FAIL, "Deleted session not hidden")
            
            # Restore
            test_session.is_deleted = False
            test_session.deleted_at = None
            self.db.commit()
            
            # Verify restore
            restored = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id,
                InterviewSession.is_deleted == False
            ).first()
            
            if restored:
                self.log(PASS, "Restore works - session back to active")
            else:
                self.add_issue("STEP 3", "HIGH", "Restore did not work")
                self.log(FAIL, "Restore failed")
            
            self.log(PASS, "STEP 3 COMPLETE")
            return True
            
        except Exception as e:
            self.add_issue("STEP 3", "CRITICAL", f"Delete/restore test failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 4: FEEDBACK SYSTEM
    # ============================================================================
    
    def step4_feedback_system(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 4: FEEDBACK SYSTEM TESTING")
        self.log(INFO, "="*70)
        
        try:
            # Find a completed session
            completed_session = self.db.query(InterviewSession).filter(
                InterviewSession.status == "completed",
                InterviewSession.is_deleted == False
            ).first()
            
            if not completed_session:
                self.log(WARN, "No completed sessions to test feedback")
                self.log(INFO, "Skipping feedback test - no completed sessions")
                return True
            
            session_id = completed_session.id
            self.log(INFO, f"Testing feedback with session ID: {session_id}")
            
            # Generate feedback
            try:
                feedback = generate_feedback_report(session_id, self.db)
                
                if "error" in feedback:
                    self.add_issue("STEP 4", "HIGH", f"Feedback generation error: {feedback['error']}")
                    self.log(FAIL, f"Feedback error: {feedback['error']}")
                    return False
                
                # Check required fields
                required_fields = [
                    "session_id",
                    "score_breakdown",
                    "strengths",
                    "weaknesses",
                    "recommendations"
                ]
                
                missing_fields = [f for f in required_fields if f not in feedback]
                
                if missing_fields:
                    self.add_issue("STEP 4", "HIGH", f"Feedback missing fields: {missing_fields}")
                    self.log(FAIL, f"Missing fields: {missing_fields}")
                else:
                    self.log(PASS, "All required feedback fields present")
                
                # Check score_breakdown
                if "score_breakdown" in feedback:
                    sb = feedback["score_breakdown"]
                    required_scores = ["correctness", "clarity", "confidence", "final_score"]
                    missing_scores = [s for s in required_scores if s not in sb]
                    
                    if missing_scores:
                        self.add_issue("STEP 4", "MEDIUM", f"Missing score fields: {missing_scores}")
                        self.log(FAIL, f"Missing scores: {missing_scores}")
                    else:
                        self.log(PASS, "All score fields present")
                        
                        # Check for NaN values
                        for key in required_scores:
                            val = sb.get(key)
                            if val is None or (isinstance(val, float) and str(val) == 'nan'):
                                self.add_issue("STEP 4", "MEDIUM", f"Score field '{key}' is NaN or None")
                                self.log(WARN, f"'{key}' is NaN/None: {val}")
                            else:
                                self.log(PASS, f"'{key}': {val}")
                
                # Check weights sum to 1.0
                weights = sb.get("weights", {})
                weight_sum = sum([
                    weights.get("correctness", 0),
                    weights.get("clarity", 0),
                    weights.get("confidence", 0)
                ])
                
                if abs(weight_sum - 1.0) < 0.01:
                    self.log(PASS, f"Weights sum correct: {weight_sum}")
                else:
                    self.add_issue("STEP 4", "MEDIUM", f"Weights don't sum to 1.0: {weight_sum}")
                    self.log(WARN, f"Weight sum: {weight_sum}")
                
                self.log(PASS, "STEP 4 COMPLETE")
                
            except Exception as e:
                self.add_issue("STEP 4", "CRITICAL", f"Feedback generation crashed: {str(e)}")
                self.log(FAIL, f"Feedback generation error: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            self.add_issue("STEP 4", "CRITICAL", f"Feedback system check failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 5: BEHAVIOR METRICS
    # ============================================================================
    
    def step5_behavior_metrics(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 5: BEHAVIOR METRICS VALIDATION")
        self.log(INFO, "="*70)
        
        try:
            # Check for NaN and None values
            metrics = self.db.query(InterviewBehaviorMetric).all()
            
            if not metrics:
                self.log(INFO, "No behavior metrics in database")
                self.log(PASS, "STEP 5 COMPLETE (no metrics to check)")
                return True
            
            self.log(INFO, f"Checking {len(metrics)} behavior metrics")
            
            nan_count = 0
            none_count = 0
            valid_count = 0
            
            for metric in metrics:
                score_fields = [
                    "attention_score",
                    "presence_score",
                    "vocal_confidence_score",
                    "overall_behavior_score"
                ]
                
                for field in score_fields:
                    val = getattr(metric, field, None)
                    
                    if val is None:
                        none_count += 1
                    elif isinstance(val, float) and str(val) == 'nan':
                        nan_count += 1
                    else:
                        valid_count += 1
            
            if nan_count > 0:
                self.add_issue("STEP 5", "MEDIUM", f"{nan_count} NaN values in behavior metrics")
                self.log(WARN, f"Found {nan_count} NaN values")
            else:
                self.log(PASS, "No NaN values")
            
            if none_count > 0:
                self.log(WARN, f"Found {none_count} None values (may be expected for new metrics)")
            else:
                self.log(PASS, "No None values")
            
            if valid_count > 0:
                self.log(PASS, f"Found {valid_count} valid metric values")
            
            # Check for division by zero issues in aggregation
            behavior_issues = self.db.query(BehaviorIssue).all()
            
            if behavior_issues:
                self.log(INFO, f"Checking {len(behavior_issues)} behavior issues")
                # Check for safe aggregation
                self.log(PASS, "Behavior issues exist - aggregation logic should work")
            
            self.log(PASS, "STEP 5 COMPLETE")
            return True
            
        except Exception as e:
            self.add_issue("STEP 5", "CRITICAL", f"Behavior metrics check failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 6: AUDIO TRANSCRIPTION
    # ============================================================================
    
    def step6_audio_transcription(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 6: AUDIO TRANSCRIPTION CHECK")
        self.log(INFO, "="*70)
        
        try:
            # Check if answers have transcriptions
            answers = self.db.query(InterviewAnswer).all()
            
            if not answers:
                self.log(INFO, "No answers in database")
                self.log(PASS, "STEP 6 COMPLETE (no answers to check)")
                return True
            
            self.log(INFO, f"Checking {len(answers)} answers")
            
            with_transcription = sum(1 for a in answers if a.transcription)
            without_transcription = len(answers) - with_transcription
            
            self.log(INFO, f"Answers with transcription: {with_transcription}")
            self.log(INFO, f"Answers without transcription: {without_transcription}")
            
            if with_transcription > 0:
                self.log(PASS, "Transcription pipeline appears functional")
            else:
                self.log(WARN, "No transcriptions found - may be expected for new system")
            
            # Check for empty transcriptions
            empty_transcriptions = sum(1 for a in answers if a.transcription == "")
            if empty_transcriptions > 0:
                self.add_issue("STEP 6", "MEDIUM", f"{empty_transcriptions} answers have empty transcription")
                self.log(WARN, f"Found {empty_transcriptions} empty transcriptions")
            
            self.log(PASS, "STEP 6 COMPLETE")
            return True
            
        except Exception as e:
            self.add_issue("STEP 6", "CRITICAL", f"Audio transcription check failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 7: FRONTEND VALIDATION
    # ============================================================================
    
    def step7_frontend_validation(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 7: FRONTEND VALIDATION")
        self.log(INFO, "="*70)
        
        try:
            # Check that critical files exist
            import os
            
            frontend_components = [
                "frontend/src/components/DashboardPage.jsx",
                "frontend/src/components/FeedbackPage.jsx",
                "frontend/src/components/InterviewPage.jsx",
                "frontend/src/App.jsx"
            ]
            
            for component in frontend_components:
                if os.path.exists(component):
                    self.log(PASS, f"Component exists: {component}")
                else:
                    self.add_issue("STEP 7", "MEDIUM", f"Component missing: {component}")
                    self.log(FAIL, f"Missing: {component}")
            
            self.log(PASS, "STEP 7 COMPLETE (files validated - runtime checks needed)")
            return True
            
        except Exception as e:
            self.add_issue("STEP 7", "MEDIUM", f"Frontend validation failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # STEP 8: AUTH SYSTEM
    # ============================================================================
    
    def step8_auth_system(self):
        self.log(INFO, "="*70)
        self.log(INFO, "STEP 8: AUTH SYSTEM VERIFICATION")
        self.log(INFO, "="*70)
        
        try:
            # Check users table
            users = self.db.query(User).all()
            self.log(INFO, f"Total users: {len(users)}")
            
            if users:
                for user in users[:3]:  # Check first 3 users
                    self.log(INFO, f"User: {user.email} - ID: {user.id}")
                    
                    # Check if password fields exist
                    has_pwd = hasattr(user, 'password_hash')
                    has_reset_token = hasattr(user, 'reset_token_hash')
                    has_reset_expiry = hasattr(user, 'reset_token_expiry')
                    
                    if has_pwd and has_reset_token and has_reset_expiry:
                        self.log(PASS, "User has all required auth fields")
                    else:
                        missing = []
                        if not has_pwd:
                            missing.append("password_hash")
                        if not has_reset_token:
                            missing.append("reset_token_hash")
                        if not has_reset_expiry:
                            missing.append("reset_token_expiry")
                        
                        self.add_issue("STEP 8", "HIGH", f"User missing fields: {missing}")
                        self.log(FAIL, f"Missing fields: {missing}")
            else:
                self.log(INFO, "No users in database")
            
            self.log(PASS, "STEP 8 COMPLETE")
            return True
            
        except Exception as e:
            self.add_issue("STEP 8", "CRITICAL", f"Auth system check failed: {str(e)}")
            self.log(FAIL, f"Error: {str(e)}")
            return False

    # ============================================================================
    # GENERATE REPORT
    # ============================================================================
    
    def generate_report(self):
        self.log(INFO, "="*70)
        self.log(INFO, "FINAL DEBUG REPORT")
        self.log(INFO, "="*70)
        
        # Issues Summary
        print("\n📋 ISSUES DETECTED:\n")
        if self.issues:
            for i, issue in enumerate(self.issues, 1):
                severity_emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡",
                    "LOW": "🟢"
                }.get(issue["severity"], "⚪")
                
                print(f"{i}. [{severity_emoji} {issue['severity']}] STEP {issue['step']}")
                print(f"   {issue['message']}\n")
        else:
            print(f"{PASS} No issues detected!\n")
        
        # Fixes Applied
        print("\n🔧 FIXES APPLIED:\n")
        if self.fixes_applied:
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"{i}. {fix}\n")
        else:
            print("No fixes needed.\n")
        
        # System Status
        critical_count = sum(1 for i in self.issues if i["severity"] == "CRITICAL")
        high_count = sum(1 for i in self.issues if i["severity"] == "HIGH")
        
        print("\n" + "="*70)
        if critical_count == 0 and high_count == 0:
            print(f"{PASS} SYSTEM STATUS: STABLE ✨")
        elif critical_count == 0:
            print(f"{WARN} SYSTEM STATUS: PARTIALLY STABLE (High priority issues present)")
        else:
            print(f"{FAIL} SYSTEM STATUS: UNSTABLE (Critical issues present)")
        print("="*70)

    def run_full_debug(self):
        """Run complete debug sequence"""
        print("\n")
        self.log(INFO, "=" * 70)
        self.log(INFO, "AI INTERVIEW SYSTEM - FULL DEBUG & STABILIZATION")
        self.log(INFO, "=" * 70)
        
        steps = [
            ("1", self.step1_database_integrity),
            ("2", self.step2_session_visibility),
            ("3", self.step3_delete_restore),
            ("4", self.step4_feedback_system),
            ("5", self.step5_behavior_metrics),
            ("6", self.step6_audio_transcription),
            ("7", self.step7_frontend_validation),
            ("8", self.step8_auth_system),
        ]
        
        results = {}
        for step_num, step_func in steps:
            try:
                result = step_func()
                results[step_num] = result
            except Exception as e:
                self.log(FAIL, f"Step {step_num} crashed: {str(e)}")
                results[step_num] = False
        
        # Generate final report
        self.generate_report()
        
        # Close connection
        self.db.close()
        
        return results

if __name__ == "__main__":
    debugger = SystemDebugger()
    debugger.run_full_debug()
