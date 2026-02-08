#!/usr/bin/env python3
"""
Database setup script for AlphaVelocity
Creates database, user, and initializes schema
"""

import sys
import subprocess

def run_psql_command(command, database='postgres'):
    """Run a psql command"""
    try:
        # Try without password first (trust authentication)
        result = subprocess.run(
            ['psql', '-U', 'postgres', '-d', database, '-c', command],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"✅ Success: {command[:50]}...")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def setup_database():
    """Set up the AlphaVelocity database"""

    print("🚀 Setting up AlphaVelocity database...")
    print()

    # Step 1: Check if database exists
    print("1️⃣ Checking if database exists...")
    check_db = run_psql_command(
        "SELECT 1 FROM pg_database WHERE datname='alphavelocity'"
    )

    # Step 2: Create database if it doesn't exist
    print("\n2️⃣ Creating database...")
    run_psql_command("CREATE DATABASE alphavelocity")

    # Step 3: Create user
    print("\n3️⃣ Creating user...")
    run_psql_command(
        "CREATE USER alphavelocity WITH PASSWORD 'alphavelocity_secure_password'"
    )

    # Step 4: Grant privileges
    print("\n4️⃣ Granting privileges...")
    run_psql_command("GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity")

    # Step 5: Grant schema privileges
    print("\n5️⃣ Granting schema privileges...")
    run_psql_command("GRANT ALL ON SCHEMA public TO alphavelocity", database='alphavelocity')

    print("\n✅ Database setup complete!")
    print("\nNow run the migration script:")
    print("  python simple_db_migration.py")

def create_tables():
    """Create database tables"""
    print("\n6️⃣ Creating database tables...")

    try:
        sys.path.insert(0, '/alpha_velocity')
        from backend.database.config import db_config

        # Test connection
        if not db_config.test_connection():
            print("❌ Cannot connect to database")
            return False

        # Create tables
        db_config.create_all_tables()
        print("✅ Tables created successfully!")
        return True

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    setup_database()

    # Ask if user wants to create tables
    response = input("\nCreate database tables now? (y/n): ")
    if response.lower() == 'y':
        create_tables()
