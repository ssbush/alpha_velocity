-- Set password for postgres superuser
ALTER USER postgres PASSWORD 'postgresql_admin_password';

-- Create alphavelocity database
CREATE DATABASE alphavelocity;

-- Create alphavelocity user with password
CREATE USER alphavelocity WITH PASSWORD 'alphavelocity_secure_password';

-- Grant all privileges on alphavelocity database to alphavelocity user
GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity;