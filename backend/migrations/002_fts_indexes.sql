-- Full-text search indexes for PostgreSQL
-- Adds generated tsvector columns and GIN indexes for fast text search

-- Problems
ALTER TABLE problems ADD COLUMN IF NOT EXISTS fts_tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))) STORED;
CREATE INDEX IF NOT EXISTS idx_problems_fts ON problems USING GIN (fts_tsvector);

-- Goals
ALTER TABLE goals ADD COLUMN IF NOT EXISTS fts_tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))) STORED;
CREATE INDEX IF NOT EXISTS idx_goals_fts ON goals USING GIN (fts_tsvector);

-- Projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS fts_tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))) STORED;
CREATE INDEX IF NOT EXISTS idx_projects_fts ON projects USING GIN (fts_tsvector);

-- Knowledge items
ALTER TABLE knowledge_items ADD COLUMN IF NOT EXISTS fts_tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,''))) STORED;
CREATE INDEX IF NOT EXISTS idx_knowledge_fts ON knowledge_items USING GIN (fts_tsvector);

-- Decisions
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS fts_tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(proposal,''))) STORED;
CREATE INDEX IF NOT EXISTS idx_decisions_fts ON decisions USING GIN (fts_tsvector);
