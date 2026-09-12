-- ============================================================
-- CareerOS Migration 025: Phase 12 Application Lifecycle & Follow-up Intelligence
-- ============================================================

-- 1. Persistent Application Lifecycle Records
CREATE TABLE IF NOT EXISTS application_lifecycle_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL, -- references application_packages(id) or applications(id)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    current_status TEXT NOT NULL CHECK (current_status IN (
        'DISCOVERED',
        'PREPARED',
        'REVIEW_REQUIRED',
        'APPROVED',
        'HANDOFF',
        'SUBMITTED',
        'ACKNOWLEDGED',
        'SCREENING',
        'INTERVIEW',
        'ASSESSMENT',
        'OFFER',
        'REJECTED',
        'WITHDRAWN',
        'NO_RESPONSE',
        'ARCHIVED'
    )),
    last_transition_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_lifecycle_user_app UNIQUE (user_id, application_id)
);

-- 2. Auditable Status Transitions with Evidence
CREATE TABLE IF NOT EXISTS application_lifecycle_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lifecycle_id UUID NOT NULL REFERENCES application_lifecycle_records(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN (
        'USER_CONFIRMATION',
        'RECRUITER_COMMUNICATION',
        'PORTAL_STATUS',
        'IMPORTED_EMAIL',
        'API_RESPONSE',
        'MANUALLY_ENTERED'
    )),
    evidence_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor TEXT NOT NULL DEFAULT 'USER',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Follow-up Recommendations
CREATE TABLE IF NOT EXISTS follow_up_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lifecycle_id UUID NOT NULL REFERENCES application_lifecycle_records(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'DISMISSED', 'SENT')),
    recommended_send_date TIMESTAMPTZ NOT NULL,
    template_subject TEXT NOT NULL,
    template_body TEXT NOT NULL,
    user_notes TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lifecycle_user_id ON application_lifecycle_records(user_id);
CREATE INDEX IF NOT EXISTS idx_lifecycle_status ON application_lifecycle_records(current_status);
CREATE INDEX IF NOT EXISTS idx_lifecycle_app_id ON application_lifecycle_records(application_id);
CREATE INDEX IF NOT EXISTS idx_transitions_lifecycle_id ON application_lifecycle_transitions(lifecycle_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_lifecycle_id ON follow_up_recommendations(lifecycle_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_user_status ON follow_up_recommendations(user_id, status);

-- Enable Row Level Security
ALTER TABLE application_lifecycle_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_lifecycle_transitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_up_recommendations ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies for application_lifecycle_records
CREATE POLICY "Users can view their own application lifecycles"
    ON application_lifecycle_records FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own application lifecycles"
    ON application_lifecycle_records FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own application lifecycles"
    ON application_lifecycle_records FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- User Isolation RLS Policies for application_lifecycle_transitions
CREATE POLICY "Users can view their own transitions"
    ON application_lifecycle_transitions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own transitions"
    ON application_lifecycle_transitions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- User Isolation RLS Policies for follow_up_recommendations
CREATE POLICY "Users can view their own follow up recommendations"
    ON follow_up_recommendations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own follow up recommendations"
    ON follow_up_recommendations FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can insert their own follow up recommendations"
    ON follow_up_recommendations FOR INSERT
    WITH CHECK (auth.uid() = user_id);
