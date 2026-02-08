#!/usr/bin/env python3
"""Create database tables for AlphaVelocity"""

import sys
sys.path.insert(0, '/alpha_velocity')

from backend.database.config import db_config

def create_tables():
    """Create all database tables"""
    print("📊 Creating AlphaVelocity database tables...")
    print("=" * 50)

    try:
        # Test connection first
        print("\n1️⃣  Testing database connection...")
        if not db_config.test_connection():
            print("❌ Cannot connect to database")
            print("\nMake sure:")
            print("  - PostgreSQL is running")
            print("  - Database 'alphavelocity' exists")
            print("  - User 'alphavelocity' has proper privileges")
            return False

        print("✅ Connection successful!")

        # Create tables
        print("\n2️⃣  Creating tables...")
        db_config.create_all_tables()

        print("\n✅ All tables created successfully!")
        print("\n" + "=" * 50)
        print("Database is ready!")
        print("\nNext steps:")
        print("  1. Restart backend if running")
        print("  2. Access http://localhost:3000")
        print("  3. Click 'Sign Up' to create your first user")

        return True

    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_tables()
