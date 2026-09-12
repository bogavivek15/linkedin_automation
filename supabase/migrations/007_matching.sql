-- ============================================================
-- CareerOS Migration 007: Hybrid Matching & Decision Cache
-- ============================================================

-- Job Matches (USER-OWNED)
CREATE TABLE IF NOT EXISTS job_matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  
  -- Overall & Sub-scores (0-100)
  overall_score NUMERIC(5, 2) NOT NULL,
  semantic_score NUMERIC(5, 2) NOT NULL,
  skills_score NUMERIC(5, 2) NOT NULL,
  experience_score NUMERIC(5, 2) NOT NULL,
  location_score NUMERIC(5, 2) NOT NULL,
  preferences_score NUMERIC(5, 2) NOT NULL,
  
  -- Hard Constraint Gate
  has_hard_constraint_violation BOOLEAN NOT NULL DEFAULT FALSE,
  hard_constraint_reasons TEXT[] DEFAULT '{}',
  
  -- Composite Decision Signal
  final_decision_score NUMERIC(5, 2) NOT NULL, -- 0.90 * Match + 0.10 * Trust
  action_decision TEXT NOT NULL, -- 'AUTO_APPLY', 'USER_APPROVAL', 'REJECT'
  
  -- Audit & Versioning Trail
  matching_version TEXT NOT NULL DEFAULT 'matching_v1.0',
  policy_version TEXT NOT NULL DEFAULT 'policy_v1.0',
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  UNIQUE(profile_id, job_id)
);
