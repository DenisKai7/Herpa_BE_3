-- Migration 003: AI Usage Enhanced
-- Adds columns to model_usage_events for comprehensive AI usage tracking
-- Adds soft delete support for AI usage logs

-- Add new columns to model_usage_events
ALTER TABLE model_usage_events
  ADD COLUMN IF NOT EXISTS persona text,
  ADD COLUMN IF NOT EXISTS endpoint text,
  ADD COLUMN IF NOT EXISTS provider text DEFAULT 'local',
  ADD COLUMN IF NOT EXISTS prompt_text text,
  ADD COLUMN IF NOT EXISTS response_text text,
  ADD COLUMN IF NOT EXISTS retrieval_context jsonb,
  ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
  ADD COLUMN IF NOT EXISTS deleted_by uuid REFERENCES auth.users(id);

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_model_usage_persona ON model_usage_events(persona) WHERE persona IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_model_usage_endpoint ON model_usage_events(endpoint) WHERE endpoint IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_model_usage_deleted_at ON model_usage_events(deleted_at) WHERE deleted_at IS NOT NULL;
