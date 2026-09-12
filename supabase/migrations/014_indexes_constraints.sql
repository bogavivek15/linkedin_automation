-- ============================================================
-- CareerOS Migration 014: Indexes & Performance Constraints
-- ============================================================

-- 1. B-Tree Indexes for Foreign Keys & High-Frequency Lookups
CREATE INDEX IF NOT EXISTS idx_career_profiles_user_id ON career_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_profile_skills_user_id ON profile_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_chunks_resume_id ON resume_chunks(resume_id);
CREATE INDEX IF NOT EXISTS idx_resume_claims_user_id ON resume_claims(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_claims_resume_id ON resume_claims(resume_id);
CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_source_external ON jobs(source, external_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_user_id ON job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_job_id ON job_matches(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_request_id ON agent_runs(request_id);

-- 2. HNSW Vector Indexes (Fast Approximate Nearest Neighbor Search for 768-dim embeddings)
CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw 
  ON jobs USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_resume_chunks_embedding_hnsw 
  ON resume_chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_skills_embedding_hnsw 
  ON skills USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_projects_embedding_hnsw 
  ON projects USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
