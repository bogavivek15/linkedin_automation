-- ============================================================
-- CareerOS Migration 024: Phase 11 Controlled Application Execution & User Handoff
-- ============================================================

-- 1. Application Executions: Safe, Idempotent Execution Records
CREATE TABLE IF NOT EXISTS application_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_package_id UUID NOT NULL REFERENCES application_packages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    decision_id UUID REFERENCES decisions(id) ON DELETE SET NULL,

    execution_mode TEXT NOT NULL CHECK (execution_mode IN ('API', 'USER_HANDOFF', 'UNSUPPORTED', 'UNKNOWN')),
    status TEXT NOT NULL CHECK (status IN (
        'PREPARED',
        'READY_FOR_REVIEW',
        'APPROVED',
        'EXECUTION_CHECK',
        'BLOCKED',
        'USER_HANDOFF',
        'API_EXECUTION',
        'EXECUTING',
        'SUBMITTED',
        'VERIFIED',
        'FAILED',
        'CANCELLED',
        'EXPIRED'
    )),

    -- Idempotency: Unique key per execution attempt
    idempotency_key TEXT NOT NULL UNIQUE,

    -- Execution receipts and handoff tracking
    receipt JSONB NOT NULL DEFAULT '{}'::jsonb,
    handoff_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    safety_gate_results JSONB NOT NULL DEFAULT '{}'::jsonb,

    failure_reason TEXT,
    notes TEXT,

    submitted_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Execution Audit Events
CREATE TABLE IF NOT EXISTS execution_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES application_executions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'EXECUTION_STARTED',
        'EXECUTION_BLOCKED',
        'HANDOFF_CREATED',
        'HANDOFF_OPENED',
        'USER_MARKED_SUBMITTED',
        'API_SUBMISSION_STARTED',
        'API_SUBMITTED',
        'SUBMISSION_VERIFIED',
        'EXECUTION_FAILED',
        'EXECUTION_CANCELLED'
    )),
    actor TEXT NOT NULL DEFAULT 'SYSTEM', -- 'SYSTEM', 'USER', 'API_WORKER'
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Performance and query indexes
CREATE INDEX IF NOT EXISTS idx_executions_user_id ON application_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_executions_package_id ON application_executions(application_package_id);
CREATE INDEX IF NOT EXISTS idx_executions_job_id ON application_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON application_executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_created_at ON application_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_exec_audit_execution_id ON execution_audit_events(execution_id);
CREATE INDEX IF NOT EXISTS idx_exec_audit_user_id ON execution_audit_events(user_id);

-- Enable Row Level Security
ALTER TABLE application_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_audit_events ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies for application_executions
CREATE POLICY "Users can view their own executions"
    ON application_executions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own executions"
    ON application_executions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own executions"
    ON application_executions FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own executions"
    ON application_executions FOR DELETE
    USING (auth.uid() = user_id);

-- User Isolation RLS Policies for execution_audit_events
CREATE POLICY "Users can view their own execution audit events"
    ON execution_audit_events FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own execution audit events"
    ON execution_audit_events FOR INSERT
    WITH CHECK (auth.uid() = user_id);
