#!/usr/bin/env python3
"""
Database Setup Script for AlphaVelocity

Sets up PostgreSQL database and runs initial migration
"""

import sys
import os
import subprocess
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def install_postgresql():
    """Install PostgreSQL if not available"""
    print("🐘 Checking PostgreSQL installation...")

    try:
        result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ PostgreSQL is already installed")
            return True
    except:
        pass

    print("   📦 PostgreSQL not found, attempting installation...")

    # Try different package managers
    installers = [
        ['apt-get', 'update', '&&', 'apt-get', 'install', '-y', 'postgresql', 'postgresql-contrib'],
        ['yum', 'install', '-y', 'postgresql-server', 'postgresql-contrib'],
        ['brew', 'install', 'postgresql'],
        ['pacman', '-S', '--noconfirm', 'postgresql']
    ]

    for installer in installers:
        try:
            result = subprocess.run(installer, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Installed PostgreSQL using {installer[0]}")
                return True
        except FileNotFoundError:
            continue

    print("   ❌ Could not install PostgreSQL automatically")
    print("      Please install PostgreSQL manually and rerun this script")
    return False

def setup_database():
    """Create database and user"""
    print("🗄️  Setting up AlphaVelocity database...")

    commands = [
        # Create database
        "CREATE DATABASE alphavelocity;",
        # Create user
        "CREATE USER alphavelocity WITH PASSWORD 'alphavelocity';",
        # Grant privileges
        "GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity;",
        # Grant schema privileges
        "GRANT ALL ON SCHEMA public TO alphavelocity;"
    ]

    for cmd in commands:
        try:
            result = subprocess.run([
                'psql', '-h', 'localhost', '-U', 'postgres', '-c', cmd
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(f"   ✅ {cmd[:20]}...")
            else:
                if "already exists" in result.stderr:
                    print(f"   ℹ️  {cmd[:20]}... (already exists)")
                else:
                    print(f"   ❌ {cmd[:20]}... Error: {result.stderr}")
        except Exception as e:
            print(f"   ❌ Error executing command: {e}")

def install_python_dependencies():
    """Install required Python packages"""
    print("🐍 Installing Python dependencies...")

    requirements_file = Path(__file__).parent.parent / "requirements.txt"

    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("   ✅ Python dependencies installed")
        else:
            print(f"   ❌ Error installing dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error installing dependencies: {e}")
        return False

    return True

def create_env_file():
    """Create .env file with database configuration"""
    print("🔧 Creating environment configuration...")

    env_file = Path(__file__).parent.parent / ".env"
    env_content = """# AlphaVelocity Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=alphavelocity
DB_USER=alphavelocity
DB_PASSWORD=alphavelocity

# Application Settings
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
"""

    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("   ✅ Created .env file")
    else:
        print("   ℹ️  .env file already exists")

def run_migration():
    """Run database migration"""
    print("📊 Running database migration...")

    try:
        # Import and run migration
        from database.migration import DatabaseMigration

        migration = DatabaseMigration()
        migration.run_full_migration()
        print("   ✅ Migration completed successfully")
        return True
    except Exception as e:
        print(f"   ❌ Migration failed: {e}")
        return False

def main():
    """Main setup process"""
    print("🚀 AlphaVelocity Database Setup")
    print("=" * 40)

    # Step 1: Install PostgreSQL (if needed)
    if not install_postgresql():
        return False

    # Step 2: Install Python dependencies
    if not install_python_dependencies():
        return False

    # Step 3: Create environment file
    create_env_file()

    # Step 4: Setup database
    setup_database()

    # Step 5: Run migration
    if run_migration():
        print("\n🎉 Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the backend server: python -m uvicorn backend.main:app --reload")
        print("2. Access the API at: http://localhost:8000")
        print("3. View API docs at: http://localhost:8000/docs")
    else:
        print("\n❌ Setup completed with errors. Please check the migration output above.")

if __name__ == "__main__":
    main()