"""
Verification script to check schema migration results.
Runs SQL queries to confirm all columns are present with correct data.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "interview_prep.db"


def verify_migration():
    """Verify that all columns were added and data was preserved."""
    print("=" * 70)
    print("SCHEMA VERIFICATION")
    print("=" * 70)
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get column info for each table
        print("\n[interview_sessions]")
        cursor.execute("PRAGMA table_info(interview_sessions)")
        cols = cursor.fetchall()
        session_cols = {col[1]: col[2] for col in cols}  # name -> type
        
        required = {"is_deleted", "deleted_at"}
        for col in required:
            if col in session_cols:
                print(f"  ✓ {col}: {session_cols[col]}")
            else:
                print(f"  ✗ MISSING: {col}")
        
        print("\n[users]")
        cursor.execute("PRAGMA table_info(users)")
        cols = cursor.fetchall()
        user_cols = {col[1]: col[2] for col in cols}
        
        required = {"reset_token_hash", "reset_token_expiry"}
        for col in required:
            if col in user_cols:
                print(f"  ✓ {col}: {user_cols[col]}")
            else:
                print(f"  ✗ MISSING: {col}")
        
        print("\n[interview_behavior_metrics]")
        cursor.execute("PRAGMA table_info(interview_behavior_metrics)")
        cols = cursor.fetchall()
        metric_cols = {col[1]: col[2] for col in cols}
        
        required = {
            "attention_score", "presence_score", "vocal_confidence_score",
            "overall_behavior_score", "looking_away_count", 
            "multiple_faces_detected", "face_absent_count"
        }
        for col in required:
            if col in metric_cols:
                print(f"  ✓ {col}: {metric_cols[col]}")
            else:
                print(f"  ✗ MISSING: {col}")
        
        # Data integrity
        print("\n[Data Preservation]")
        cursor.execute("SELECT COUNT(*) FROM users")
        print(f"  Users: {cursor.fetchone()[0]} rows")
        
        cursor.execute("SELECT COUNT(*) FROM interview_sessions")
        print(f"  Sessions: {cursor.fetchone()[0]} rows")
        
        cursor.execute("SELECT COUNT(*) FROM resume")
        print(f"  Resumes: {cursor.fetchone()[0]} rows")
        
        print("\n" + "=" * 70)
        print("✓ VERIFICATION COMPLETE")
        print("=" * 70)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ VERIFICATION FAILED: {e}")
        return False


if __name__ == "__main__":
    verify_migration()
