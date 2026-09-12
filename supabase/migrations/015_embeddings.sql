-- ============================================================
-- CareerOS Migration 015: Embeddings & Vector Metadata Cache
-- ============================================================

-- Generic embedding records for traceable vector metadata and content-hash caching
CREATE TABLE IF NOT EXISTS embedding_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL, -- 'RESUME_CHUNK', 'PROJECT', 'SKILL', 'PROFILE', 'JOB'
  entity_id UUID NOT NULL,
  source_type TEXT,
  source_id UUID,
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL DEFAULT 'v1',
  dimensions INT NOT NULL DEFAULT 768,
  content_hash TEXT NOT NULL,
  embedding vector(768) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(content_hash, model_name, dimensions)
);

-- Enable RLS
ALTER TABLE embedding_records ENABLE ROW LEVEL SECURITY;

-- Users can view their own embedding records
CREATE POLICY "Users view their own embedding records"
  ON embedding_records FOR SELECT TO authenticated
  USING (auth.uid() = user_id OR user_id IS NULL);

-- Users manage their own embedding records
CREATE POLICY "Users manage their own embedding records"
  ON embedding_records FOR ALL TO authenticated
  USING (auth.uid() = user_id);

-- Indexes for efficient lookup and deduplication
CREATE INDEX IF NOT EXISTS idx_embedding_records_user_id ON embedding_records(user_id);
CREATE INDEX IF NOT EXISTS idx_embedding_records_entity ON embedding_records(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_embedding_records_hash ON embedding_records(content_hash, model_name, dimensions);

-- HNSW Vector Index for fast Approximate Nearest Neighbor Search
CREATE INDEX IF NOT EXISTS idx_embedding_records_embedding_hnsw 
  ON embedding_records USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
