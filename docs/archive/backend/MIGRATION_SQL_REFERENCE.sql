-- ============================================================================
-- SAFE SCHEMA MIGRATION SQL REFERENCE
-- These are the SQL commands that were (or would have been) executed
-- ============================================================================

-- MIGRATION STEP 1: interview_sessions TABLE
-- ============================================================================
-- Add soft delete tracking columns for session archive functionality

-- Check if column exists before adding (to avoid duplicate errors)
-- PRAGMA table_info(interview_sessions); -- View existing columns

ALTER TABLE interview_sessions ADD COLUMN is_deleted BOOLEAN DEFAULT 0;
ALTER TABLE interview_sessions ADD COLUMN deleted_at DATETIME;

-- Verify columns were added:
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='interview_sessions';


-- MIGRATION STEP 2: users TABLE
-- ============================================================================
-- Add password reset functionality columns

-- Check existing columns:
-- PRAGMA table_info(users);

ALTER TABLE users ADD COLUMN reset_token_hash TEXT;
ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME;

-- Verify columns were added:
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='users';


-- MIGRATION STEP 3: interview_behavior_metrics TABLE
-- ============================================================================
-- Add new composite score and count columns for behavioral analysis

-- Check existing columns:
-- PRAGMA table_info(interview_behavior_metrics);

ALTER TABLE interview_behavior_metrics ADD COLUMN attention_score FLOAT;
ALTER TABLE interview_behavior_metrics ADD COLUMN presence_score FLOAT;
ALTER TABLE interview_behavior_metrics ADD COLUMN vocal_confidence_score FLOAT;
ALTER TABLE interview_behavior_metrics ADD COLUMN overall_behavior_score FLOAT;
ALTER TABLE interview_behavior_metrics ADD COLUMN looking_away_count INTEGER;
ALTER TABLE interview_behavior_metrics ADD COLUMN multiple_faces_detected INTEGER;
ALTER TABLE interview_behavior_metrics ADD COLUMN face_absent_count INTEGER;

-- These columns already existed (added previously):
-- - speech_rate_stability
-- - pause_hesitation
-- - pitch_variation
-- - vocal_energy

-- Verify columns were added:
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='interview_behavior_metrics';


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- View all columns in each table:
-- ============================================================================
PRAGMA table_info(interview_sessions);
PRAGMA table_info(users);
PRAGMA table_info(interview_behavior_metrics);


-- Check data preservation:
-- ============================================================================
SELECT COUNT(*) as total_users FROM users;
SELECT COUNT(*) as total_sessions FROM interview_sessions;
SELECT COUNT(*) as total_answers FROM interview_answers;
SELECT COUNT(*) as total_metrics FROM interview_behavior_metrics;


-- Soft delete validation:
-- ============================================================================
-- Show active sessions (visible in dashboard)
SELECT id, user_id, status, is_deleted, deleted_at 
FROM interview_sessions 
WHERE is_deleted = 0;

-- Show deleted sessions (hidden from dashboard)
SELECT id, user_id, status, is_deleted, deleted_at 
FROM interview_sessions 
WHERE is_deleted = 1;


-- Password reset tracking:
-- ============================================================================
-- Show users with active reset tokens
SELECT id, email, reset_token_hash, reset_token_expiry 
FROM users 
WHERE reset_token_hash IS NOT NULL AND reset_token_expiry IS NOT NULL;


-- Behavior metrics validation:
-- ============================================================================
-- Show composite behavior scores
SELECT 
    id, 
    session_id, 
    attention_score, 
    presence_score, 
    vocal_confidence_score, 
    overall_behavior_score
FROM interview_behavior_metrics
WHERE overall_behavior_score IS NOT NULL;


-- Check for referential integrity issues:
-- ============================================================================
-- Orphaned answer records (answers without parent session)
SELECT COUNT(*) as orphaned_answers
FROM interview_answers 
WHERE session_id NOT IN (SELECT id FROM interview_sessions);

-- Orphaned behavior metrics
SELECT COUNT(*) as orphaned_metrics
FROM interview_behavior_metrics 
WHERE session_id NOT IN (SELECT id FROM interview_sessions);


-- ============================================================================
-- BACKUP BEFORE MIGRATION (Run this if re-migrating)
-- ============================================================================
-- To create a backup of current database before any changes:
-- VACUUM INTO 'interview_prep_backup_' || strftime('%Y%m%d_%H%M%S', 'now') || '.db';


-- ============================================================================
-- ROLLBACK REFERENCE (If something goes wrong)
-- ============================================================================
-- SQLite does not have DROP COLUMN support, so rollback requires:
-- 1. Create new table with original schema
-- 2. Copy data from old table
-- 3. Drop old table
-- 4. Rename new table
-- This is why using ALTER TABLE ADD COLUMN is safer (only adds, never removes)
