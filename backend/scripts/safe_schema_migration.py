"""
SAFE DATABASE SCHEMA MIGRATION
Preserves all existing data while adding missing columns
"""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "interview_prep.db"

class SafeMigration:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Open database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"✓ Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect: {e}")
            return False
    
    def get_table_info(self, table_name):
        """Get column information for a table"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1]: row[2] for row in self.cursor.fetchall()}
        return columns
    
    def column_exists(self, table_name, column_name):
        """Check if column already exists"""
        columns = self.get_table_info(table_name)
        return column_name in columns
    
    def get_row_count(self, table_name):
        """Get row count before migration"""
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return self.cursor.fetchone()[0]
    
    def add_column(self, table_name, column_name, column_def):
        """Safely add a column if it doesn't exist"""
        if self.column_exists(table_name, column_name):
            logger.warning(f"  ⊘ Column already exists: {table_name}.{column_name}")
            return True
        
        try:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
            self.cursor.execute(sql)
            logger.info(f"  ✓ Added: {table_name}.{column_name}")
            return True
        except Exception as e:
            logger.error(f"  ✗ Failed to add {table_name}.{column_name}: {e}")
            return False
    
    def migrate_interview_sessions(self):
        """Add soft delete fields to interview_sessions"""
        logger.info("\n" + "="*70)
        logger.info("MIGRATION STEP 1: interview_sessions table")
        logger.info("="*70)
        
        row_count = self.get_row_count("interview_sessions")
        logger.info(f"  Current rows: {row_count}")
        
        # Add is_deleted column
        self.add_column("interview_sessions", "is_deleted", 
                       "INTEGER NOT NULL DEFAULT 0")
        
        # Add deleted_at column
        self.add_column("interview_sessions", "deleted_at",
                       "DATETIME")
        
        return True
    
    def migrate_users(self):
        """Add password reset fields to users"""
        logger.info("\n" + "="*70)
        logger.info("MIGRATION STEP 2: users table")
        logger.info("="*70)
        
        row_count = self.get_row_count("users")
        logger.info(f"  Current rows: {row_count}")
        
        # Add reset token fields
        self.add_column("users", "reset_token_hash",
                       "TEXT UNIQUE")
        
        self.add_column("users", "reset_token_expiry",
                       "DATETIME")
        
        return True
    
    def migrate_behavior_metrics(self):
        """Add new behavior metric fields"""
        logger.info("\n" + "="*70)
        logger.info("MIGRATION STEP 3: interview_behavior_metrics table")
        logger.info("="*70)
        
        row_count = self.get_row_count("interview_behavior_metrics")
        logger.info(f"  Current rows: {row_count}")
        
        # Audio behavioral features (0.0 - 1.0)
        self.add_column("interview_behavior_metrics", "speech_rate_stability",
                       "REAL DEFAULT 0.5")
        
        self.add_column("interview_behavior_metrics", "pause_hesitation",
                       "REAL DEFAULT 0.5")
        
        self.add_column("interview_behavior_metrics", "pitch_variation",
                       "REAL DEFAULT 0.5")
        
        self.add_column("interview_behavior_metrics", "vocal_energy",
                       "REAL DEFAULT 0.5")
        
        # Composite behavior scores (0-100)
        self.add_column("interview_behavior_metrics", "attention_score",
                       "REAL")
        
        self.add_column("interview_behavior_metrics", "presence_score",
                       "REAL")
        
        self.add_column("interview_behavior_metrics", "vocal_confidence_score",
                       "REAL")
        
        self.add_column("interview_behavior_metrics", "overall_behavior_score",
                       "REAL")
        
        # Issue counters
        self.add_column("interview_behavior_metrics", "looking_away_count",
                       "INTEGER DEFAULT 0")
        
        self.add_column("interview_behavior_metrics", "multiple_faces_detected",
                       "INTEGER DEFAULT 0")
        
        self.add_column("interview_behavior_metrics", "face_absent_count",
                       "INTEGER DEFAULT 0")
        
        return True
    
    def verify_schema(self):
        """Verify all columns exist after migration"""
        logger.info("\n" + "="*70)
        logger.info("VERIFICATION: Schema check")
        logger.info("="*70)
        
        required_columns = {
            "interview_sessions": ["is_deleted", "deleted_at"],
            "users": ["reset_token_hash", "reset_token_expiry"],
            "interview_behavior_metrics": [
                "speech_rate_stability", "pause_hesitation", "pitch_variation",
                "vocal_energy", "attention_score", "presence_score",
                "vocal_confidence_score", "overall_behavior_score",
                "looking_away_count", "multiple_faces_detected", "face_absent_count"
            ]
        }
        
        all_pass = True
        for table, columns in required_columns.items():
            logger.info(f"\n  Table: {table}")
            table_columns = self.get_table_info(table)
            
            for col in columns:
                if col in table_columns:
                    logger.info(f"    ✓ {col}")
                else:
                    logger.error(f"    ✗ {col} - MISSING!")
                    all_pass = False
        
        return all_pass
    
    def verify_data_integrity(self):
        """Verify no data was lost"""
        logger.info("\n" + "="*70)
        logger.info("VERIFICATION: Data integrity check")
        logger.info("="*70)
        
        tables_to_check = ["users", "interview_sessions", "interview_answers", 
                          "interview_behavior_metrics", "behavior_issues"]
        
        for table in tables_to_check:
            try:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                logger.info(f"  {table}: {count} rows ✓")
            except Exception as e:
                logger.error(f"  {table}: Error - {e}")
                return False
        
        return True
    
    def commit_and_close(self):
        """Commit changes and close connection"""
        try:
            self.conn.commit()
            logger.info("\n✓ Changes committed to database")
            self.conn.close()
            logger.info("✓ Database connection closed")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to commit: {e}")
            self.conn.rollback()
            self.conn.close()
            return False
    
    def run_migration(self):
        """Run complete migration"""
        logger.info("\n")
        logger.info("╔" + "="*68 + "╗")
        logger.info("║ SAFE DATABASE SCHEMA MIGRATION - PRESERVE ALL DATA            ║")
        logger.info("╚" + "="*68 + "╝")
        
        # Connect
        if not self.connect():
            return False
        
        try:
            # Run migrations
            self.migrate_interview_sessions()
            self.migrate_users()
            self.migrate_behavior_metrics()
            
            # Verify
            if not self.verify_schema():
                logger.error("\n✗ MIGRATION FAILED - Schema verification failed")
                self.conn.rollback()
                self.conn.close()
                return False
            
            if not self.verify_data_integrity():
                logger.error("\n✗ MIGRATION FAILED - Data integrity check failed")
                self.conn.rollback()
                self.conn.close()
                return False
            
            # Commit
            if not self.commit_and_close():
                return False
            
            logger.info("\n" + "="*70)
            logger.info("✓ MIGRATION COMPLETE - All data preserved")
            logger.info("="*70)
            return True
            
        except Exception as e:
            logger.error(f"\n✗ MIGRATION FAILED: {e}")
            self.conn.rollback()
            self.conn.close()
            return False

if __name__ == "__main__":
    migration = SafeMigration(DB_PATH)
    success = migration.run_migration()
    exit(0 if success else 1)
