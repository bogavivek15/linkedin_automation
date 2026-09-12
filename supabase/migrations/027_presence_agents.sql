-- ============================================================
-- CareerOS Migration 027: Phase 15 & Phase 16
-- Professional Presence Intelligence & Agent Registry
-- ============================================================

-- 1. Enhanced Presence Posts Table (USER-SCOPED)
CREATE TABLE IF NOT EXISTS presence_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  profile_id UUID NOT NULL,
  content_type TEXT NOT NULL DEFAULT 'LINKEDIN_POST',
  title TEXT NOT NULL,
  content_body TEXT NOT NULL,
  grounding_evidence_ids UUID[] DEFAULT '{}',
  quality_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0 CHECK (quality_score >= 0.0 AND quality_score <= 100.0),
  validation_status TEXT NOT NULL DEFAULT 'DRAFT', -- 'IDEA', 'DRAFT', 'EVIDENCE_CHECK', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'REJECTED'
  publication_mode TEXT NOT NULL DEFAULT 'USER_HANDOFF', -- 'USER_HANDOFF', 'OFFICIAL_API'
  publication_evidence JSONB DEFAULT '{}'::jsonb,
  scheduled_for TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS for presence_posts
ALTER TABLE presence_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own presence posts"
  ON presence_posts
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_presence_posts_user_status ON presence_posts (user_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_presence_posts_scheduled ON presence_posts (scheduled_for) WHERE scheduled_for IS NOT NULL;

-- 2. Agent Registry Table (System Read-Only for Tenanted Users)
CREATE TABLE IF NOT EXISTS agent_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name TEXT UNIQUE NOT NULL,
  agent_version TEXT NOT NULL DEFAULT '1.0.0',
  category TEXT NOT NULL,
  capabilities TEXT[] NOT NULL DEFAULT '{}',
  permissions TEXT[] NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'IDLE', 'STANDBY', 'MAINTENANCE'
  last_run_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE agent_registry ENABLE ROW LEVEL SECURITY;

CREATE POLICY "All authenticated users can read agent registry"
  ON agent_registry
  FOR SELECT
  TO authenticated
  USING (true);

-- Seed the 8 Core CareerOS Agents
INSERT INTO agent_registry (agent_name, agent_version, category, capabilities, permissions, status)
VALUES
  (
    'Orchestrator Agent',
    '2.0.0',
    'ORCHESTRATION',
    ARRAY['graph_dispatch', 'state_transition_gate', 'pipeline_coordination'],
    ARRAY['execute_graph', 'emit_audit_event'],
    'ACTIVE'
  ),
  (
    'Opportunity Agent',
    '1.5.0',
    'DISCOVERY',
    ARRAY['canonical_normalization', 'deduplication', 'staleness_detection'],
    ARRAY['read_jobs', 'write_canonical_jobs'],
    'ACTIVE'
  ),
  (
    'Trust & Safety Agent',
    '2.1.0',
    'SECURITY',
    ARRAY['scam_detection', 'domain_impersonation_analysis', 'evidence_grounding'],
    ARRAY['read_jobs', 'write_trust_assessments', 'block_high_risk'],
    'ACTIVE'
  ),
  (
    'Profile Agent',
    '1.2.0',
    'IDENTITY',
    ARRAY['resume_parsing', 'skill_normalization', 'evidence_graph_linking'],
    ARRAY['read_resumes', 'write_skills', 'write_projects'],
    'ACTIVE'
  ),
  (
    'Application Agent',
    '2.0.0',
    'EXECUTION_PREP',
    ARRAY['diff_generation', 'claim_citation', 'qa_generation', 'safety_gating'],
    ARRAY['read_jobs', 'read_resumes', 'write_application_packages'],
    'ACTIVE'
  ),
  (
    'Presence Agent',
    '1.0.0',
    'OUTREACH',
    ARRAY['achievement_synthesis', 'linkedin_drafting', 'grounded_content_validation'],
    ARRAY['read_memories', 'write_presence_drafts'],
    'ACTIVE'
  ),
  (
    'Learning Agent',
    '1.0.0',
    'FEEDBACK',
    ARRAY['outcome_aggregation', 'pattern_detection', 'insight_synthesis'],
    ARRAY['read_outcomes', 'write_patterns', 'write_insights'],
    'ACTIVE'
  ),
  (
    'Memory Agent',
    '1.1.0',
    'KNOWLEDGE',
    ARRAY['provenance_tracking', 'vector_relational_retrieval', 'fact_verification'],
    ARRAY['read_memories', 'propose_memories'],
    'ACTIVE'
  )
ON CONFLICT (agent_name) DO UPDATE SET
  agent_version = EXCLUDED.agent_version,
  capabilities = EXCLUDED.capabilities,
  permissions = EXCLUDED.permissions,
  status = EXCLUDED.status,
  updated_at = NOW();
