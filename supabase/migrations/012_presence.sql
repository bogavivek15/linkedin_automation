-- ============================================================
-- CareerOS Migration 012: Professional Presence & Publishing
-- ============================================================

-- Presence Content (USER-OWNED)
CREATE TABLE IF NOT EXISTS presence_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  content_type TEXT NOT NULL DEFAULT 'LINKEDIN_POST', -- 'LINKEDIN_POST', 'PROJECT_SHOWCASE', 'TECH_INSIGHT'
  grounding_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
  cited_claim_ids UUID[] DEFAULT '{}',
  
  -- Human Approval State
  status TEXT NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'ARCHIVED'
  scheduled_for TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  external_post_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
