-- ============================================================
-- CareerOS Migration 026: Phase 13 & 14 Career Learning, Feedback Loop & Memory System
-- ============================================================

-- 1. Career Outcomes (Phase 13)
CREATE TABLE IF NOT EXISTS career_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    application_id UUID REFERENCES application_packages(id) ON DELETE SET NULL,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    outcome_type TEXT NOT NULL CHECK (outcome_type IN (
        'CALLBACK',
        'SCREENING_PASSED',
        'INTERVIEW_SCHEDULED',
        'OFFER',
        'REJECTED_SCREEN',
        'REJECTED_TECHNICAL',
        'REJECTED_FINAL',
        'NO_RESPONSE',
        'WITHDRAWN'
    )),
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    tailored_resume_id UUID REFERENCES tailored_resumes(id) ON DELETE SET NULL,
    match_score NUMERIC(5,2),
    trust_score NUMERIC(5,2),
    notes TEXT,
    extracted_skill_gaps TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Detected Career Patterns (Phase 13)
CREATE TABLE IF NOT EXISTS career_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'SKILL_DEMAND_SURGE',
        'INTERVIEW_CONVERSION_BOOST',
        'REJECTION_SKILL_GAP',
        'RESUME_VERSION_SUPERIORITY',
        'ROLE_AFFINITY'
    )),
    summary TEXT NOT NULL,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 1.0,
    evidence_sample_count INTEGER NOT NULL DEFAULT 1,
    evidence_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Career Insights (Phase 13)
CREATE TABLE IF NOT EXISTS career_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN (
        'STRATEGY',
        'SKILL_GAP',
        'RESUME_OPTIMIZATION',
        'ROLE_FIT',
        'CONVERSION_TREND'
    )),
    severity TEXT NOT NULL DEFAULT 'INFO' CHECK (severity IN ('INFO', 'RECOMMENDATION', 'CRITICAL')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    actionable_recommendation TEXT,
    supporting_pattern_ids UUID[] DEFAULT '{}',
    dismissed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Persistent Structured Career Memory (Phase 14)
CREATE TABLE IF NOT EXISTS persistent_career_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN (
        'PROFILE',
        'SKILL',
        'PROJECT',
        'EXPERIENCE',
        'EDUCATION',
        'CERTIFICATION',
        'PREFERENCE',
        'GOAL',
        'APPLICATION',
        'OUTCOME',
        'FEEDBACK',
        'INSIGHT',
        'PRESENCE'
    )),
    key TEXT NOT NULL,
    content TEXT NOT NULL,
    provenance TEXT NOT NULL,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 1.0,
    verification_status TEXT NOT NULL DEFAULT 'AI_PROPOSED' CHECK (verification_status IN (
        'UNVERIFIED',
        'AI_PROPOSED',
        'EVIDENCE_VALIDATED',
        'USER_CONFIRMED',
        'AUTHORITATIVE'
    )),
    source_event TEXT,
    source_ref_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_memories_user_category_key UNIQUE (user_id, category, key)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_outcomes_user ON career_outcomes(user_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_app ON career_outcomes(application_id);
CREATE INDEX IF NOT EXISTS idx_patterns_user ON career_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_user ON career_insights(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_cat ON persistent_career_memories(user_id, category);

-- Enable Row Level Security
ALTER TABLE career_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE persistent_career_memories ENABLE ROW LEVEL SECURITY;

-- User Isolation Policies
CREATE POLICY "Users can view own outcomes" ON career_outcomes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own outcomes" ON career_outcomes FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own patterns" ON career_patterns FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own patterns" ON career_patterns FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own insights" ON career_insights FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own insights" ON career_insights FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own insights" ON career_insights FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own memories" ON persistent_career_memories FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own memories" ON persistent_career_memories FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own memories" ON persistent_career_memories FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own memories" ON persistent_career_memories FOR DELETE USING (auth.uid() = user_id);
