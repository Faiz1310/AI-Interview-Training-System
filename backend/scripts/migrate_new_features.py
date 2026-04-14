"""
Database Migration Script
Adds missing columns to existing tables for new features:
- Feature 1: Soft Delete (Session)
- Feature 3: Forgot Password (User)
- Feature 4: Behavior Metrics Enhancement
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Apply database migrations for new features"""
    
    db_path = os.path.join(os.path.dirname(__file__), "interview_prep.db")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found! Creating new database...")
        from database import init_db
        init_db()
        print("✅ New database created")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n" + "="*70)
        print("DATABASE MIGRATION - Adding Missing Columns")
        print("="*70)
        
        # Get existing tables and their columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📋 Found tables: {[t[0] for t in tables]}")
        
        # ─── Migration 1: Users table (Feature 3: Forgot Password) ────────
        print("\n[Migration 1] Users table - Password Reset Fields")
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "reset_token_hash" not in columns:
            print("  ⚠️  Missing reset_token_hash column")
            cursor.execute("""
                ALTER TABLE users ADD COLUMN reset_token_hash TEXT UNIQUE
            """)
            print("  ✅ Added reset_token_hash column")
        else:
            print("  ✅ reset_token_hash column exists")
        
        if "reset_token_expiry" not in columns:
            print("  ⚠️  Missing reset_token_expiry column")
            cursor.execute("""
                ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME
            """)
            print("  ✅ Added reset_token_expiry column")
        else:
            print("  ✅ reset_token_expiry column exists")
        
        # ─── Migration 2: Interview Sessions table (Feature 1: Soft Delete) ──
        print("\n[Migration 2] Interview Sessions table - Soft Delete Fields")
        cursor.execute("PRAGMA table_info(interview_sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "is_deleted" not in columns:
            print("  ⚠️  Missing is_deleted column")
            cursor.execute("""
                ALTER TABLE interview_sessions ADD COLUMN is_deleted BOOLEAN DEFAULT 0
            """)
            print("  ✅ Added is_deleted column")
        else:
            print("  ✅ is_deleted column exists")
        
        if "deleted_at" not in columns:
            print("  ⚠️  Missing deleted_at column")
            cursor.execute("""
                ALTER TABLE interview_sessions ADD COLUMN deleted_at DATETIME
            """)
            print("  ✅ Added deleted_at column")
        else:
            print("  ✅ deleted_at column exists")
        
        # ─── Migration 3: Behavior Metrics table (Feature 4: Enhancement) ─────
        print("\n[Migration 3] Behavior Metrics table - Enhanced Scoring Fields")
        cursor.execute("PRAGMA table_info(interview_behavior_metrics)")
        columns = [col[1] for col in cursor.fetchall()]
        
        new_columns = {
            "speech_rate_stability": "FLOAT",
            "pause_hesitation": "FLOAT",
            "pitch_variation": "FLOAT",
            "vocal_energy": "FLOAT",
            "attention_score": "FLOAT",
            "presence_score": "FLOAT",
            "vocal_confidence_score": "FLOAT",
            "overall_behavior_score": "FLOAT",
            "looking_away_count": "INTEGER DEFAULT 0",
            "multiple_faces_detected": "INTEGER DEFAULT 0",
            "face_absent_count": "INTEGER DEFAULT 0",
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                print(f"  ⚠️  Missing {col_name} column")
                cursor.execute(f"""
                    ALTER TABLE interview_behavior_metrics 
                    ADD COLUMN {col_name} {col_type}
                """)
                print(f"  ✅ Added {col_name} column")
            else:
                print(f"  ✅ {col_name} column exists")
        
        conn.commit()
        print("\n" + "="*70)
        print("✅ DATABASE MIGRATION COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        
    except sqlite3.OperationalError as e:
        print(f"\n❌ Migration Error: {e}")
        print("   This error typically occurs if columns already exist.")
        print("   If the column exists but is different, you may need to:")
        print("   1. Backup the database")
        print("   2. Delete interview_prep.db")
        print("   3. Let init_db() create a fresh database")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
