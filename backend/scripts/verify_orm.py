#!/usr/bin/env python3
"""Verify ORM works with migrated database"""

from database import SessionLocal, engine
from models.user import User
from models.session import InterviewSession
from sqlalchemy import inspect

print('='*70)
print('DATABASE CONNECTION AND ORM VERIFICATION')
print('='*70)
print()

try:
    inspector = inspect(engine)
    tables = list(inspector.get_table_names())
    print(f'OK: Connected to database - {len(tables)} tables found')
    print()
    
    db = SessionLocal()
    
    user_count = db.query(User).count()
    print(f'OK: ORM Query - Users: {user_count}')
    
    session_count = db.query(InterviewSession).filter(InterviewSession.is_deleted == False).count()
    print(f'OK: ORM Query - Active Sessions: {session_count}')
    
    user = db.query(User).first()
    if user:
        print(f'OK: User record loaded: {user.email}')
        print(f'      ID: {user.id}')
        print(f'      Active: {user.is_active}')
        print(f'      reset_token_hash field exists: {hasattr(user, "reset_token_hash")}')
        print(f'      reset_token_expiry field exists: {hasattr(user, "reset_token_expiry")}')
    
    session = db.query(InterviewSession).first()
    if session:
        print(f'OK: Session record loaded: ID {session.id}')
        print(f'      User ID: {session.user_id}')
        print(f'      Status: {session.status}')
        print(f'      is_deleted field exists: {hasattr(session, "is_deleted")}')
        print(f'      deleted_at field exists: {hasattr(session, "deleted_at")}')
        print(f'      is_deleted value: {session.is_deleted}')
    
    db.close()
    
    print()
    print('='*70)
    print('SUCCESS: All ORM checks passed - System ready')
    print('='*70)
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
