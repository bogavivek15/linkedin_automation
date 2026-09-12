-- ============================================================
-- CareerOS Migration 004: Resumes, Chunks & Verifiable Claims
-- ============================================================

-- Resumes table (USER-OWNED)
CREATE TABLE IF NOT EXISTS resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL DEFAULT 'Master Resume',
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size INT NOT NULL,
  mime_type TEXT NOT NULL,
  raw_text TEXT,
  parsed_content JSONB,
  is_master BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Resume Chunks for semantic embedding & targeted retrieval
CREATE TABLE IF NOT EXISTS resume_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  section_type TEXT NOT NULL, -- 'SUMMARY', 'EXPERIENCE', 'PROJECTS', 'EDUCATION', 'SKILLS'
  content TEXT NOT NULL,
  chunk_index INT NOT NULL,
  embedding vector(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Verifiable Resume Claims (FIRST-CLASS PROVENANCE DOMAIN)
-- Lineage: Claim -> Source -> Evidence -> Verification Status -> Allowed Usage
CREATE TABLE IF NOT EXISTS resume_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  claim_type TEXT NOT NULL, -- 'SKILL', 'METRIC', 'RESPONSIBILITY', 'CREDENTIAL', 'OUTCOME'
  statement TEXT NOT NULL,
  source_type TEXT NOT NULL, -- 'PROJECT', 'EXPERIENCE', 'EDUCATION', 'CERTIFICATION'
  source_id UUID, -- References projects.id or other source record when applicable
  evidence_text TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'UNCERTAIN', -- 'VERIFIED', 'INFERRED', 'UNCERTAIN', 'REJECTED'
  confidence_score NUMERIC(4, 3) DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),
  allowed_in_tailoring BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
