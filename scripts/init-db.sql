-- Initialize StruMind Database
-- This script sets up the initial database structure

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS projects;
CREATE SCHEMA IF NOT EXISTS models;
CREATE SCHEMA IF NOT EXISTS analysis;
CREATE SCHEMA IF NOT EXISTS design;
CREATE SCHEMA IF NOT EXISTS bim;

-- Set default search path
ALTER DATABASE strumind SET search_path TO public, auth, projects, models, analysis, design, bim;

-- Create initial admin user (for development only)
-- Password: admin123 (hashed)
-- This should be removed in production
INSERT INTO auth.users (id, email, password_hash, is_active, is_superuser, created_at)
VALUES (
    uuid_generate_v4(),
    'admin@strumind.com',
    crypt('admin123', gen_salt('bf')),
    true,
    true,
    NOW()
) ON CONFLICT (email) DO NOTHING;