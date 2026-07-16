-- Add stepik_id column for Stepik OAuth integration
ALTER TABLE users ADD COLUMN IF NOT EXISTS stepik_id INTEGER;
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_stepik_id ON users(stepik_id);
