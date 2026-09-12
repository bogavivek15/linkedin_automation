-- ============================================================
-- CareerOS Migration 002: Career Profiles & User Preferences
-- ============================================================

-- Career Profiles table
CREATE TABLE IF NOT EXISTS career_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  headline TEXT,
  career_summary TEXT,
  location TEXT,
  avatar_url TEXT,
  education JSONB DEFAULT '[]'::jsonb,
  experience JSONB DEFAULT '[]'::jsonb,
  profile_completeness INT DEFAULT 0 CHECK (profile_completeness >= 0 AND profile_completeness <= 100),
  embedding vector(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  profile_id UUID NOT NULL REFERENCES career_profiles(id) ON DELETE CASCADE,
  target_roles TEXT[] DEFAULT '{}',
  target_industries TEXT[] DEFAULT '{}',
  target_companies TEXT[] DEFAULT '{}',
  preferred_locations TEXT[] DEFAULT '{}',
  preferred_work_modes TEXT[] DEFAULT '{REMOTE, HYBRID}',
  preferred_employment_types TEXT[] DEFAULT '{FULL_TIME}',
  salary_min NUMERIC(12, 2),
  salary_max NUMERIC(12, 2),
  salary_currency TEXT DEFAULT 'USD',
  auto_apply_enabled BOOLEAN DEFAULT FALSE,
  auto_apply_threshold INT DEFAULT 90,
  min_trust_score INT DEFAULT 80,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
