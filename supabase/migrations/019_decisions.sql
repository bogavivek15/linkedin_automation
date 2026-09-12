-- ============================================================
-- CareerOS Migration 019: Phase 9 Deterministic Decisions Table
-- ============================================================

CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    match_id UUID REFERENCES job_matches(id) ON DELETE SET NULL,
    trust_assessment_id UUID REFERENCES trust_assessments(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Trust-weighted composite score: Final = 0.90 * M + 0.10 * T
    overall_score NUMERIC(5,2) NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    match_score NUMERIC(5,2) NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    trust_score NUMERIC(5,2) NOT NULL CHECK (trust_score >= 0 AND trust_score <= 100),

    risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'UNKNOWN')),
    confidence TEXT NOT NULL CHECK (confidence IN ('LOW', 'MEDIUM', 'HIGH')),
    action TEXT NOT NULL CHECK (action IN ('AUTO_APPLY', 'USER_APPROVAL', 'REJECT', 'IMPROVEMENT_REQUIRED')),

    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocking_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,

    eligible_for_auto_apply BOOLEAN NOT NULL DEFAULT false,
    hard_constraints_passed BOOLEAN NOT NULL DEFAULT true,
    approval_required BOOLEAN NOT NULL DEFAULT true,
    application_mode TEXT NOT NULL DEFAULT 'USER_HANDOFF' CHECK (application_mode IN ('API', 'USER_HANDOFF', 'UNSUPPORTED', 'UNKNOWN')),

    policy_version TEXT NOT NULL DEFAULT 'v1',
    decision_version TEXT NOT NULL DEFAULT 'v1',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Idempotency constraint: single active decision per profile and job
    CONSTRAINT uq_decisions_profile_job UNIQUE (profile_id, job_id)
);

-- Performance and query indexes
CREATE INDEX IF NOT EXISTS idx_decisions_profile_created ON decisions(profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_profile_job ON decisions(profile_id, job_id);
CREATE INDEX IF NOT EXISTS idx_decisions_user_id ON decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_action ON decisions(action);
CREATE INDEX IF NOT EXISTS idx_decisions_overall_score ON decisions(overall_score DESC);

-- Enable RLS
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies
CREATE POLICY "Users can view their own decisions"
    ON decisions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own decisions"
    ON decisions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own decisions"
    ON decisions FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
