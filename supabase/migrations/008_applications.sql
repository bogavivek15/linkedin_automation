-- ============================================================
-- CareerOS Migration 008: Applications & State Machine
-- ============================================================

-- Applications (USER-OWNED)
CREATE TABLE IF NOT EXISTS applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  match_id UUID REFERENCES job_matches(id) ON DELETE SET NULL,
  
  -- State Machine
  -- 'DISCOVERED' -> 'MATCHED' -> 'PENDING_APPROVAL' -> 'APPROVED' -> 'SUBMITTING' -> 'SUBMITTED' -> 'INTERVIEWING' -> 'OFFER' / 'REJECTED'
  status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
  
  submission_mode TEXT NOT NULL DEFAULT 'MANUAL', -- 'AUTO', 'MANUAL_HANDOFF', 'API'
  applied_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  -- Idempotency: Candidate cannot create multiple active applications for same job
  CONSTRAINT uq_user_job_application UNIQUE(user_id, job_id)
);

-- Tailored Application Artifacts (Linked to verifiable claims)
CREATE TABLE IF NOT EXISTS tailored_resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  base_resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content JSONB NOT NULL,
  included_claim_ids UUID[] DEFAULT '{}', -- Traceability: exactly which claims were incorporated
  cover_letter TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Application State Transition Audit Trail
CREATE TABLE IF NOT EXISTS application_state_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  actor TEXT NOT NULL, -- 'SYSTEM_POLICY', 'USER', 'BACKGROUND_WORKER'
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
