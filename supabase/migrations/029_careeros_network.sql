-- ============================================================
-- CareerOS Migration 029: Phase 19
-- CareerOS Network: Controlled Professional Environment & Social Graph
-- ============================================================

-- 1. Network Profiles (Directory of Professionals, Mentors, Recruiters, and Candidates)
CREATE TABLE IF NOT EXISTS network_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  handle TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  headline TEXT NOT NULL,
  avatar_url TEXT,
  banner_url TEXT,
  company TEXT,
  location TEXT,
  about TEXT,
  skills TEXT[] DEFAULT '{}',
  experience JSONB DEFAULT '[]'::jsonb,
  match_score INT DEFAULT 85,
  is_target BOOLEAN DEFAULT false,
  role_type TEXT DEFAULT 'ENGINEER', -- 'ENGINEER', 'RECRUITER', 'FOUNDER', 'STUDENT'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Network Posts (Professional Feed)
CREATE TABLE IF NOT EXISTS network_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id UUID NOT NULL REFERENCES network_profiles(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  media_url TEXT,
  likes_count INT DEFAULT 0,
  comments_count INT DEFAULT 0,
  tags TEXT[] DEFAULT '{}',
  agent_relevance_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Network Comments (Feed Interactions)
CREATE TABLE IF NOT EXISTS network_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES network_posts(id) ON DELETE CASCADE,
  author_id UUID NOT NULL REFERENCES network_profiles(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  agent_drafted BOOLEAN DEFAULT false,
  evidence_citation TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Network Connections (Social Graph & Agent Outreach Tracking)
CREATE TABLE IF NOT EXISTS network_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  target_profile_id UUID NOT NULL REFERENCES network_profiles(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'CONNECTED', 'REJECTED'
  outreach_note TEXT,
  agent_generated BOOLEAN DEFAULT false,
  evidence_grounding TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Network Messages (Chat Threads with Recruiters & Connections)
CREATE TABLE IF NOT EXISTS network_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  sender_id UUID NOT NULL REFERENCES network_profiles(id) ON DELETE CASCADE,
  receiver_id UUID NOT NULL REFERENCES network_profiles(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  agent_generated BOOLEAN DEFAULT false,
  evidence_grounding TEXT,
  read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE network_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE network_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE network_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE network_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE network_messages ENABLE ROW LEVEL SECURITY;

-- Read policies (Network is open to authenticated users)
CREATE POLICY "Public read for network profiles" ON network_profiles FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY "Public read for network posts" ON network_posts FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY "Public read for network comments" ON network_comments FOR SELECT TO authenticated, anon USING (true);

CREATE POLICY "Users can manage own network connections" ON network_connections FOR ALL TO authenticated
  USING (auth.uid() = user_id OR user_id IS NULL)
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can manage own network messages" ON network_messages FOR ALL TO authenticated
  USING (auth.uid() = user_id OR user_id IS NULL)
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_network_profiles_handle ON network_profiles(handle);
CREATE INDEX IF NOT EXISTS idx_network_posts_created ON network_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_connections_user ON network_connections(user_id, target_profile_id);
CREATE INDEX IF NOT EXISTS idx_network_messages_thread ON network_messages(sender_id, receiver_id, created_at ASC);

-- Seed Initial Realistic Network Data (Profiles & Posts for Live Hackathon Demo)
INSERT INTO network_profiles (id, handle, full_name, headline, company, location, about, skills, match_score, is_target, role_type)
VALUES
  (
    'a0000000-0000-0000-0000-000000000001',
    'sarahchen',
    'Sarah Chen',
    'Senior Machine Learning Engineer @ Anthropic | Building Autonomous Agent Toolchains',
    'Anthropic',
    'San Francisco, CA',
    'Researching agentic alignment, tool grounding, and context-window optimizations for frontier LLMs.',
    ARRAY['Python', 'PyTorch', 'LangGraph', 'Agentic Systems', 'Vector Search'],
    96,
    true,
    'ENGINEER'
  ),
  (
    'a0000000-0000-0000-0000-000000000002',
    'davidkim',
    'David Kim',
    'Staff Technical Recruiter @ DeepMind | Hiring AI/Systems Research Interns & New Grads',
    'Google DeepMind',
    'New York, NY',
    'Passionate about connecting exceptional student builders with cutting-edge reinforcement learning and LLM engineering teams.',
    ARRAY['Technical Recruiting', 'AI Talent', 'University Relations', 'Engineering Leadership'],
    91,
    true,
    'RECRUITER'
  ),
  (
    'a0000000-0000-0000-0000-000000000003',
    'elenarostova',
    'Elena Rostova',
    'Co-Founder & CTO @ NexusAI (YC W24) | ex-OpenAI Systems',
    'NexusAI',
    'San Francisco, CA',
    'Scaling high-throughput deterministic LLM inference engines. Looking for passionate backend and distributed systems interns.',
    ARRAY['Rust', 'Distributed Systems', 'CUDA', 'Python', 'FastAPI'],
    88,
    true,
    'FOUNDER'
  ),
  (
    'a0000000-0000-0000-0000-000000000004',
    'marcusvance',
    'Marcus Vance',
    'Lead AI Architect @ Scale AI | Multi-Agent Coordination & Synthetic Data',
    'Scale AI',
    'Seattle, WA',
    'Architecting human-in-the-loop evaluation pipelines for enterprise agentic workflows.',
    ARRAY['Multi-Agent Systems', 'Python', 'Evaluation Metrics', 'Kubernetes'],
    84,
    false,
    'ENGINEER'
  )
ON CONFLICT (id) DO NOTHING;

-- Seed Initial Realistic Industry Posts
INSERT INTO network_posts (id, author_id, content, likes_count, comments_count, tags, agent_relevance_note)
VALUES
  (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'One of the biggest mistakes I see candidates make when applying to agentic engineering roles is claiming "hallucination-free LLM pipelines" without evidence provenance. If your system cannot cite the exact memory hash or verified document segment, it is not production ready. Grounding + deterministic guardrails is the future.',
    42,
    8,
    ARRAY['AgenticAI', 'PromptEngineering', 'MachineLearning', 'Grounding'],
    'Highly relevant to your verified LangChain evidence claims. Sarah frequently mentors students building deterministic evaluation guardrails.'
  ),
  (
    'b0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000002',
    'We just opened applications for our 2025 AI Systems & Autonomous Agents Engineering internships at DeepMind! We care far less about standard boilerplate leetcode grinding and far more about genuine open-source contributions, evidence-grounded projects, and clear problem solving. Reach out directly if you have built working agent orchestrators.',
    128,
    34,
    ARRAY['DeepMind', 'Internships', 'Hiring', 'GenerativeAI'],
    'Direct match for your primary target goal: "Generative AI Internship". Outreach Agent recommends personalized connection with verified GitHub portfolio.'
  ),
  (
    'b0000000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000003',
    'Just deployed our distributed embedding index using pgvector with HNSW indexing on 10M+ tokens. Latency dropped by 68% compared to IVFFlat. If you are a student working with pgvector and FastAPI, drop your repo link in the comments—we love hiring hands-on builders.',
    89,
    19,
    ARRAY['PostgreSQL', 'pgvector', 'FastAPI', 'HighPerformance'],
    'Matches your verified FastAPI and pgvector tech stack. Personalization Agent can generate a high-signal comment highlighting your CareerOS vector benchmark.'
  )
ON CONFLICT (id) DO NOTHING;
