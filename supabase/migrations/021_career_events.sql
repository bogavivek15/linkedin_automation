-- ============================================================
-- CareerOS Migration 021: Phase 9.x Career Events Table
-- ============================================================

CREATE TABLE IF NOT EXISTS career_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES career_runs(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Performance and query indexes
CREATE INDEX IF NOT EXISTS idx_career_events_run_timestamp ON career_events(run_id, timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_career_events_user_event_type ON career_events(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_career_events_profile_id ON career_events(profile_id);

-- Enable RLS
ALTER TABLE career_events ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies
CREATE POLICY "Users can view their own career events"
    ON career_events FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own career events"
    ON career_events FOR INSERT
    WITH CHECK (auth.uid() = user_id);
