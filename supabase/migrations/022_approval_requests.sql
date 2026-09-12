-- ============================================================
-- CareerOS Migration 022: Phase 9.x Approval Requests Table
-- ============================================================

CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES career_runs(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    decision_id UUID REFERENCES decisions(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED')),
    requested_action TEXT NOT NULL DEFAULT 'REVIEW',
    reason TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Idempotency: only one approval request per run and job
    CONSTRAINT uq_approval_run_job UNIQUE (run_id, job_id)
);

-- Performance and query indexes
CREATE INDEX IF NOT EXISTS idx_approval_requests_user_status ON approval_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_run_id ON approval_requests(run_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_job_id ON approval_requests(job_id);

-- Enable RLS
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies
CREATE POLICY "Users can view their own approval requests"
    ON approval_requests FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own approval requests"
    ON approval_requests FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own approval requests"
    ON approval_requests FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
