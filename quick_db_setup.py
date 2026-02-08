#!/usr/bin/env python3
"""Quick database setup using psycopg2 directly"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_database():
    """Create database and user"""

    # Connection parameters for postgres default database
    conn_params = {
        'host': '127.0.0.1',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': ''  # Try without password first
    }

    print("🚀 AlphaVelocity Database Setup")
    print("=" * 50)

    try:
        # Try to connect to default postgres database
        print("\n1️⃣  Connecting to PostgreSQL...")
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("✅ Connected successfully!")

        # Check if database exists
        print("\n2️⃣  Checking if 'alphavelocity' database exists...")
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname='alphavelocity'"
        )
        db_exists = cursor.fetchone() is not None

        if not db_exists:
            print("📦 Creating 'alphavelocity' database...")
            cursor.execute(sql.SQL("CREATE DATABASE alphavelocity"))
            print("✅ Database created!")
        else:
            print("✅ Database already exists!")

        # Check if user exists
        print("\n3️⃣  Checking if 'alphavelocity' user exists...")
        cursor.execute(
            "SELECT 1 FROM pg_roles WHERE rolname='alphavelocity'"
        )
        user_exists = cursor.fetchone() is not None

        if not user_exists:
            print("👤 Creating 'alphavelocity' user...")
            cursor.execute(
                "CREATE USER alphavelocity WITH PASSWORD 'alphavelocity_secure_password'"
            )
            print("✅ User created!")
        else:
            print("✅ User already exists!")

        # Grant privileges
        print("\n4️⃣  Granting privileges...")
        cursor.execute(
            "GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity"
        )
        print("✅ Privileges granted!")

        cursor.close()
        conn.close()

        # Now connect to alphavelocity database and grant schema privileges
        print("\n5️⃣  Granting schema privileges...")
        conn_params['database'] = 'alphavelocity'
        conn_params['user'] = 'postgres'
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute("GRANT ALL ON SCHEMA public TO alphavelocity")
        cursor.execute("ALTER SCHEMA public OWNER TO alphavelocity")

        # Grant default privileges
        cursor.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO alphavelocity"
        )
        cursor.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO alphavelocity"
        )

        print("✅ Schema privileges granted!")

        cursor.close()
        conn.close()

        print("\n✅ Database setup complete!")
        print("\n" + "=" * 50)
        print("Next steps:")
        print("  1. Create tables: python create_tables.py")
        print("  2. Restart backend: python -m backend.main")
        print("  3. Register a user in the frontend")
        return True

    except psycopg2.OperationalError as e:
        if 'password authentication failed' in str(e):
            print("\n❌ Password authentication failed")
            print("\nTo fix this, you need to either:")
            print("1. Set a password for postgres user")
            print("2. Or modify PostgreSQL config to allow 'trust' authentication")
            print("\nFor now, let's try option 2:")
            print("\nRun these commands:")
            print("  sudo nano /etc/postgresql/15/main/pg_hba.conf")
            print("  Change 'md5' to 'trust' for local connections")
            print("  sudo service postgresql restart")
        else:
            print(f"\n❌ Connection error: {e}")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_database()
