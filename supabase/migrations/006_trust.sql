-- ============================================================
-- CareerOS Migration 006: Trust & Safety Assessment Domain
-- ============================================================

-- Domain Reputations cache
CREATE TABLE IF NOT EXISTS domain_reputations (
  domain TEXT PRIMARY KEY,
  is_disposable_email BOOLEAN DEFAULT FALSE,
  is_free_mail BOOLEAN DEFAULT FALSE,
  is_flagged_scam BOOLEAN DEFAULT FALSE,
  whois_creation_date DATE,
  reputation_score INT DEFAULT 50 CHECK (reputation_score >= 0 AND reputation_score <= 100),
  last_checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trust Assessments for Jobs
CREATE TABLE IF NOT EXISTS trust_assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  score INT NOT NULL CHECK (score >= 0 AND score <= 100),
  risk_level TEXT NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'
  verdict TEXT NOT NULL, -- 'PASS', 'FLAGGED', 'BLOCKED'
  signals JSONB NOT NULL DEFAULT '[]'::jsonb,
  reasons TEXT[] DEFAULT '{}',
  flagged_clauses TEXT[] DEFAULT '{}',
  
  -- Versioning Metadata (Strict AI & Policy Audit Trail)
  trust_version TEXT NOT NULL DEFAULT 'trust_v1.0',
  prompt_version TEXT,
  model_provider TEXT,
  model_name TEXT,
  
  assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_trust_job UNIQUE(job_id)
);
