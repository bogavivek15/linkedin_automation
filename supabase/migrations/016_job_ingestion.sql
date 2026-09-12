-- ============================================================
-- CareerOS Migration 016: Job Ingestion, Normalization & Provenance
-- ============================================================

-- 1. Enhance jobs table with normalization, provenance & deduplication fields
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS normalized_title TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS normalized_company TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description_hash TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS normalization_version TEXT DEFAULT 'v1';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS required_skills TEXT[] DEFAULT '{}';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS preferred_skills TEXT[] DEFAULT '{}';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS experience_min NUMERIC(4, 1);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ingestion_status TEXT DEFAULT 'NORMALIZED';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS imported_by_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Index for description hash deduplication
CREATE INDEX IF NOT EXISTS idx_jobs_description_hash ON jobs(description_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_normalized_title_company ON jobs(normalized_company, normalized_title);
CREATE INDEX IF NOT EXISTS idx_jobs_imported_by_user ON jobs(imported_by_user_id);

-- 2. Multi-source Job Provenance tracking (Cross-source deduplication)
CREATE TABLE IF NOT EXISTS job_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  source TEXT NOT NULL, -- 'HIMALAYAS', 'JOBICY', 'USER_SUBMISSION', etc.
  source_url TEXT NOT NULL,
  external_id TEXT NOT NULL,
  retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_job_sources_source_external UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_job_sources_job_id ON job_sources(job_id);

-- 3. Ingestion Audit Runs
CREATE TABLE IF NOT EXISTS job_ingestion_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'RUNNING', -- 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL'
  fetched_count INTEGER DEFAULT 0,
  normalized_count INTEGER DEFAULT 0,
  deduplicated_count INTEGER DEFAULT 0,
  failed_count INTEGER DEFAULT 0,
  error_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Row Level Security (RLS)
ALTER TABLE job_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_ingestion_runs ENABLE ROW LEVEL SECURITY;

-- Job sources read policy:
-- Public jobs (where imported_by_user_id IS NULL) are readable by any authenticated user.
-- User-imported private jobs are readable only by that user.
CREATE POLICY "Authenticated users can view sources of accessible jobs"
  ON job_sources FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM jobs
      WHERE jobs.id = job_sources.job_id
        AND (jobs.imported_by_user_id IS NULL OR jobs.imported_by_user_id = auth.uid())
    )
  );

-- Ingestion runs read policy
CREATE POLICY "Authenticated users can view ingestion runs"
  ON job_ingestion_runs FOR SELECT TO authenticated USING (true);
