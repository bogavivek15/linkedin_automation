-- ============================================================
-- CareerOS Migration 003: Skills Catalog & Projects
-- ============================================================

-- Global canonical skills catalog (SHARED CATALOG)
CREATE TABLE IF NOT EXISTS skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  normalized_name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL DEFAULT 'OTHER', -- 'LANGUAGES', 'FRAMEWORKS', 'DATABASES', 'CLOUD', 'AI_ML', 'TOOLS', 'CONCEPTS', 'SOFT_SKILLS'
  description TEXT,
  embedding vector(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Profile Skills (USER-OWNED)
CREATE TABLE IF NOT EXISTS profile_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,
  proficiency TEXT NOT NULL DEFAULT 'INTERMEDIATE', -- 'BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'
  years_experience NUMERIC(4, 1),
  verified_status TEXT NOT NULL DEFAULT 'UNCERTAIN', -- 'VERIFIED', 'INFERRED', 'UNCERTAIN', 'UNKNOWN'
  source TEXT NOT NULL DEFAULT 'SELF_REPORTED', -- 'RESUME', 'PROJECT', 'GITHUB', 'ASSESSMENT', 'SELF_REPORTED'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(profile_id, skill_id)
);

-- Projects & Portfolio (USER-OWNED)
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  role TEXT,
  live_url TEXT,
  github_url TEXT,
  start_date DATE,
  end_date DATE,
  is_current BOOLEAN DEFAULT FALSE,
  verified_status TEXT NOT NULL DEFAULT 'UNCERTAIN',
  embedding vector(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Project Skills mapping
CREATE TABLE IF NOT EXISTS project_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(project_id, skill_id)
);
