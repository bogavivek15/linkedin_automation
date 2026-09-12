-- ============================================================
-- CareerOS Migration 001: PostgreSQL Extensions
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pgvector for 768-dimensional semantic embeddings
CREATE EXTENSION IF NOT EXISTS vector;
