-- ============================================================
-- CareerOS Migration 020: Phase 9.x Career Runs Table
-- ============================================================

CREATE TABLE IF NOT EXISTS career_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    request_id TEXT NOT NULL,
    graph_name TEXT NOT NULL DEFAULT 'career_intelligence',
    graph_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('QUEUED', 'RUNNING', 'WAITING_FOR_APPROVAL', 'COMPLETED', 'FAILED', 'CANCELLED')),
    current_stage TEXT NOT NULL DEFAULT 'INIT',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Performance and query indexes
CREATE INDEX IF NOT EXISTS idx_career_runs_user_status ON career_runs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_career_runs_profile_created ON career_runs(profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_career_runs_request_id ON career_runs(request_id);

-- Enable RLS
ALTER TABLE career_runs ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies
CREATE POLICY "Users can view their own career runs"
    ON career_runs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own career runs"
    ON career_runs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own career runs"
    ON career_runs FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
