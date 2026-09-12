-- ============================================================
-- CareerOS Migration 005: Companies, Jobs & Ingestion Idempotency
-- ============================================================

-- Companies (SHARED CATALOG)
CREATE TABLE IF NOT EXISTS companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  domain TEXT UNIQUE,
  logo_url TEXT,
  website_url TEXT,
  description TEXT,
  industry TEXT,
  location TEXT,
  size_range TEXT,
  verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Jobs (SHARED CATALOG)
-- Idempotency constraint: (source, external_id) prevents duplicate ingestion
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  company_name TEXT NOT NULL,
  location TEXT NOT NULL,
  work_mode TEXT NOT NULL DEFAULT 'REMOTE', -- 'REMOTE', 'HYBRID', 'ONSITE'
  employment_type TEXT NOT NULL DEFAULT 'FULL_TIME',
  description TEXT NOT NULL,
  salary_min NUMERIC(12, 2),
  salary_max NUMERIC(12, 2),
  salary_currency TEXT DEFAULT 'USD',
  application_url TEXT NOT NULL,
  source TEXT NOT NULL, -- 'HIMALAYAS', 'JOBICY', 'USER_SUBMISSION', 'DIRECT'
  external_id TEXT NOT NULL,
  posted_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  raw_payload JSONB,
  embedding vector(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_jobs_source_external UNIQUE(source, external_id)
);

-- Job Skills junction
CREATE TABLE IF NOT EXISTS job_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,
  is_required BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(job_id, skill_id)
);
