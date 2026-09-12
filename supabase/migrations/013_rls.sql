-- ============================================================
-- CareerOS Migration 013: Comprehensive Row Level Security (RLS)
-- ============================================================

-- 1. Enable RLS on all domain tables
ALTER TABLE career_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE profile_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_reputations ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE tailored_resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_state_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE correlation_trace_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_loop_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE connected_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE presence_content ENABLE ROW LEVEL SECURITY;

-- 2. SHARED CATALOG POLICIES (Read for Authenticated, Write for Service Role)
CREATE POLICY "Anyone authenticated can view skills"
  ON skills FOR SELECT TO authenticated USING (true);

CREATE POLICY "Anyone authenticated can view companies"
  ON companies FOR SELECT TO authenticated USING (true);

CREATE POLICY "Anyone authenticated can view active jobs"
  ON jobs FOR SELECT TO authenticated USING (is_active = true);

CREATE POLICY "Anyone authenticated can view job skills"
  ON job_skills FOR SELECT TO authenticated USING (true);

CREATE POLICY "Anyone authenticated can view domain reputations"
  ON domain_reputations FOR SELECT TO authenticated USING (true);

CREATE POLICY "Anyone authenticated can view trust assessments"
  ON trust_assessments FOR SELECT TO authenticated USING (true);

-- 3. USER-OWNED POLICIES (Strict isolation via auth.uid())

-- Career Profiles
CREATE POLICY "Users can view their own profile"
  ON career_profiles FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile"
  ON career_profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile"
  ON career_profiles FOR UPDATE TO authenticated USING (auth.uid() = user_id);

-- User Preferences
CREATE POLICY "Users manage their own preferences"
  ON user_preferences FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Profile Skills
CREATE POLICY "Users manage their own profile skills"
  ON profile_skills FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Projects
CREATE POLICY "Users manage their own projects"
  ON projects FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Project Skills (Ownership chain verified via project)
CREATE POLICY "Users manage project skills via project ownership"
  ON project_skills FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM projects WHERE projects.id = project_skills.project_id AND projects.user_id = auth.uid()
    )
  );

-- Resumes
CREATE POLICY "Users manage their own resumes"
  ON resumes FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Resume Chunks
CREATE POLICY "Users view their own resume chunks"
  ON resume_chunks FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Resume Claims (Verifiable provenance)
CREATE POLICY "Users manage their own resume claims"
  ON resume_claims FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Job Matches
CREATE POLICY "Users view their own job matches"
  ON job_matches FOR SELECT TO authenticated USING (auth.uid() = user_id);

-- Applications
CREATE POLICY "Users manage their own applications"
  ON applications FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Tailored Resumes (Ownership chain verified via user_id)
CREATE POLICY "Users manage their tailored resumes"
  ON tailored_resumes FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Application State History (Ownership chain via application)
CREATE POLICY "Users view application history"
  ON application_state_history FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM applications WHERE applications.id = application_state_history.application_id AND applications.user_id = auth.uid()
    )
  );

-- Agent Runs & Steps (User inspection)
CREATE POLICY "Users view their own agent runs"
  ON agent_runs FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users view their own agent steps"
  ON agent_steps FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM agent_runs WHERE agent_runs.id = agent_steps.agent_run_id AND agent_runs.user_id = auth.uid()
    )
  );

-- Career Memories
CREATE POLICY "Users manage their career memories"
  ON career_memories FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users view their feedback events"
  ON feedback_loop_events FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Connected Accounts
CREATE POLICY "Users manage their connected accounts"
  ON connected_accounts FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Presence Content
CREATE POLICY "Users manage their presence content"
  ON presence_content FOR ALL TO authenticated USING (auth.uid() = user_id);
