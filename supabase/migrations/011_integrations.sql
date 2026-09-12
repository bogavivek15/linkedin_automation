-- ============================================================
-- CareerOS Migration 011: Connected Accounts & OAuth Tokens
-- ============================================================

-- Connected External Accounts (USER-OWNED)
-- Only official permitted OAuth integrations (e.g. GitHub, LinkedIn OAuth)
CREATE TABLE IF NOT EXISTS connected_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL, -- 'GITHUB', 'LINKEDIN'
  provider_account_id TEXT NOT NULL,
  account_email TEXT,
  scopes TEXT[] DEFAULT '{}',
  access_token_encrypted TEXT, -- Server-side encrypted
  refresh_token_encrypted TEXT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, provider)
);
