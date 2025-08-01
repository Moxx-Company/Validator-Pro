#!/usr/bin/env python3
"""
Database migration script to add trial_phones_used column
"""

import os
import sys
from sqlalchemy import Column, Integer, text
from database import engine, SessionLocal
from models import User

def migrate():
    """Add trial_phones_used column to users table"""
    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'trial_phones_used'
            """))
            
            if not result.fetchone():
                # Add the new column
                conn.execute(text("ALTER TABLE users ADD COLUMN trial_phones_used INTEGER DEFAULT 0"))
                print("✅ Added trial_phones_used column to users table")
            else:
                print("ℹ️ trial_phones_used column already exists")
            
            conn.commit()
            
    except Exception as e:
        if "SQLite" in str(e) or "no such table: information_schema.columns" in str(e):
            # SQLite approach
            try:
                with engine.connect() as conn:
                    # Try to add the column (will fail if exists)
                    conn.execute(text("ALTER TABLE users ADD COLUMN trial_phones_used INTEGER DEFAULT 0"))
                    conn.commit()
                    print("✅ Added trial_phones_used column to users table (SQLite)")
            except Exception as sqlite_e:
                if "duplicate column name" in str(sqlite_e).lower():
                    print("ℹ️ trial_phones_used column already exists (SQLite)")
                else:
                    print(f"❌ SQLite migration error: {sqlite_e}")
        else:
            print(f"❌ Migration error: {e}")

if __name__ == "__main__":
    migrate()