-- ============================================================
-- CareerOS Migration 009: Agent Orchestration & Observability
-- ============================================================

-- Agent Runs (SYSTEM / USER-SCOPED)
CREATE TABLE IF NOT EXISTS agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- agent_run_id
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  request_id TEXT NOT NULL,
  graph_name TEXT NOT NULL DEFAULT 'job_discovery_and_match',
  status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'PAUSED_WAITING_APPROVAL', 'COMPLETED', 'FAILED'
  state_snapshot JSONB,
  error_message TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Agent Steps & Checkpoints
CREATE TABLE IF NOT EXISTS agent_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  step_name TEXT NOT NULL,
  agent_name TEXT NOT NULL, -- 'Orchestrator', 'Opportunity', 'Trust', 'Matching', 'Application'
  input_payload JSONB,
  output_payload JSONB,
  duration_ms INT,
  status TEXT NOT NULL, -- 'SUCCESS', 'FAILED', 'SKIPPED'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Correlation Trace Logs
CREATE TABLE IF NOT EXISTS correlation_trace_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  service TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
