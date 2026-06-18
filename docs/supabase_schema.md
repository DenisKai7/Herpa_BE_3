# Skema Supabase

Migration utama berada di `database/supabase/migrations/001_initial_schema.sql`. Trigger berada di `functions/triggers.sql`, dan policy RLS berada di `policies/rls.sql`.

Kelompok tabel:
- Identity: `profiles`, `user_preferences`.
- Chat: `chats`, `chat_messages`, `message_sources`, `shared_chats`.
- Attachment/storage: `attachments`, `attachment_jobs`, `storage_objects`.
- Recommendation: `recommendation_sessions`, `recommendation_results`.
- Quiz/gamification: `quiz_*`, `user_xp`, `user_streaks`, `badges`, `user_badges`.
- Observability: `feature_usage_events`, `model_usage_events`, `admin_audit_logs`, `system_health_logs`.
