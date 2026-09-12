-- ============================================================
-- CareerOS Migration 017: Multi-Signal Trust Evidence & Assessment
-- ============================================================

-- 1. Extend trust_assessments table with multi-signal evidence fields
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS trust_score NUMERIC(5, 2);
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5, 2);
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS confidence TEXT DEFAULT 'MEDIUM'; -- 'LOW', 'MEDIUM', 'HIGH'
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS positive_signals TEXT[] DEFAULT '{}';
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS suspicious_signals TEXT[] DEFAULT '{}';
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS missing_information TEXT[] DEFAULT '{}';
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS explanation TEXT;
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS evidence JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trust_assessments ADD COLUMN IF NOT EXISTS assessment_version TEXT DEFAULT 'v1';

-- Index for fast lookup by job_id
CREATE INDEX IF NOT EXISTS idx_trust_assessments_job_id ON trust_assessments(job_id);

-- 2. RLS Policy for trust assessments
-- Users can view trust assessments for public catalog jobs or their own imported jobs
CREATE POLICY "Users can view trust assessments for accessible jobs"
  ON trust_assessments FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM jobs
      WHERE jobs.id = trust_assessments.job_id
        AND (jobs.imported_by_user_id IS NULL OR jobs.imported_by_user_id = auth.uid())
    )
  );
