-- ============================================================
-- CareerOS Migration 010: Career Memory & Closed-Loop Learning
-- ============================================================

-- Career Memories (USER-OWNED)
CREATE TABLE IF NOT EXISTS career_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  memory_type TEXT NOT NULL, -- 'INTERVIEW_INSIGHT', 'REJECTION_FEEDBACK', 'SKILL_GAP', 'PREFERENCE_ADAPTATION'
  key TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_references JSONB DEFAULT '[]'::jsonb,
  confidence NUMERIC(4, 3) DEFAULT 1.0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Feedback Loop Events
CREATE TABLE IF NOT EXISTS feedback_loop_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  application_id UUID REFERENCES applications(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL, -- 'CALLBACK', 'OFFER', 'GHOSTED', 'REJECTED_SCREEN', 'REJECTED_FINAL'
  outcome_notes TEXT,
  extracted_skill_gaps TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
