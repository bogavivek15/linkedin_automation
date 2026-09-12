-- ============================================================
-- CareerOS Migration 023: Phase 10 Application Packages & Tailored Resumes
-- ============================================================

-- Tailored Resumes: Job-specific versions derived from base resumes with traceable diffs
DROP TABLE IF EXISTS tailored_resumes CASCADE;
CREATE TABLE IF NOT EXISTS tailored_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    base_resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    changes JSONB NOT NULL DEFAULT '[]',
    supporting_claim_ids UUID[] DEFAULT '{}',
    validation_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (validation_status IN ('DRAFT', 'VALID', 'REQUIRES_VERIFICATION', 'BLOCKED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_tailored_resume_job_version UNIQUE (user_id, job_id, base_resume_id, version)
);

-- Application Packages: Complete, verified job-specific application artifacts
CREATE TABLE IF NOT EXISTS application_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    decision_id UUID REFERENCES decisions(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    tailored_resume_id UUID REFERENCES tailored_resumes(id) ON DELETE SET NULL,
    cover_letter TEXT,
    application_answers JSONB NOT NULL DEFAULT '[]',
    selected_skills TEXT[] DEFAULT '{}',
    supporting_claim_ids UUID[] DEFAULT '{}',
    validation_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (validation_status IN ('DRAFT', 'VALIDATING', 'READY_FOR_REVIEW', 'REQUIRES_VERIFICATION', 'BLOCKED', 'APPROVED', 'EXPIRED')),
    quality_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (quality_status IN ('PENDING', 'PASSED', 'WARNING', 'FAILED')),
    quality_scores JSONB DEFAULT '{}',
    requirement_coverage JSONB DEFAULT '{}',
    warnings JSONB DEFAULT '[]',
    blocking_issues JSONB DEFAULT '[]',
    package_version TEXT NOT NULL DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Idempotency: versioned per user, job, and package_version
    CONSTRAINT uq_user_job_package_version UNIQUE (user_id, job_id, package_version)
);

-- Indexes for fast lookup & filtering
CREATE INDEX IF NOT EXISTS idx_application_packages_user_status ON application_packages(user_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_application_packages_job ON application_packages(job_id);
CREATE INDEX IF NOT EXISTS idx_application_packages_profile ON application_packages(profile_id);
CREATE INDEX IF NOT EXISTS idx_tailored_resumes_user_job ON tailored_resumes(user_id, job_id);

-- Enable Row Level Security
ALTER TABLE application_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE tailored_resumes ENABLE ROW LEVEL SECURITY;

-- User Isolation RLS Policies for application_packages
CREATE POLICY "Users can view their own application packages"
    ON application_packages FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own application packages"
    ON application_packages FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own application packages"
    ON application_packages FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own application packages"
    ON application_packages FOR DELETE
    USING (auth.uid() = user_id);

-- User Isolation RLS Policies for tailored_resumes
CREATE POLICY "Users can view their own tailored resumes"
    ON tailored_resumes FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own tailored resumes"
    ON tailored_resumes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own tailored resumes"
    ON tailored_resumes FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
