-- ============================================================
-- CareerOS Migration 018: Phase 8 Matching Enhanced Columns
-- Additive only — does not modify existing columns from 007.
-- ============================================================

-- Add Phase 8 matching detail columns to job_matches
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS resume_id UUID REFERENCES resumes(id);
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS matched_skills TEXT[] DEFAULT '{}';
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS missing_skills TEXT[] DEFAULT '{}';
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS uncertain_skills TEXT[] DEFAULT '{}';
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS match_explanation TEXT;
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS work_mode_match TEXT;
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS employment_type_match TEXT;
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS confidence TEXT DEFAULT 'MEDIUM';
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS skill_match_details JSONB DEFAULT '[]'::jsonb;
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS resume_changes TEXT[] DEFAULT '{}';
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS verification_questions TEXT[] DEFAULT '{}';
ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Performance indexes for Phase 8 queries
CREATE INDEX IF NOT EXISTS idx_job_matches_profile_job ON job_matches(profile_id, job_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_user_id ON job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_overall_score ON job_matches(overall_score DESC);
