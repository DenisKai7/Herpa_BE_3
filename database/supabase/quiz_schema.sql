-- HERPA quiz compatibility migration for current Supabase schema.
-- Uses existing tables only: quiz_subjects, quiz_modules, quiz_levels, quiz_questions,
-- quiz_question_options, quiz_attempts, quiz_answers, quiz_progress, user_xp, user_streaks.
-- Do not create quiz_topics, quiz_sessions, quiz_user_stats, or quiz_user_progress.

alter table public.quiz_levels add column if not exists quiz_type text;
alter table public.quiz_levels add column if not exists order_index integer not null default 0;

alter table public.quiz_questions add column if not exists accepted_answers jsonb not null default '[]'::jsonb;
alter table public.quiz_questions add column if not exists matching_pairs jsonb not null default '[]'::jsonb;
alter table public.quiz_questions add column if not exists order_index integer not null default 0;
alter table public.quiz_questions add column if not exists xp_reward integer not null default 10;
alter table public.quiz_questions add column if not exists options jsonb not null default '[]'::jsonb;

alter table public.quiz_attempts add column if not exists current_question_index integer not null default 0;
alter table public.quiz_attempts add column if not exists level_number integer not null default 1;
alter table public.quiz_attempts add column if not exists passed boolean;
alter table public.quiz_attempts add column if not exists metadata jsonb not null default '{}'::jsonb;

alter table public.quiz_answers add column if not exists correct_answer jsonb;
alter table public.quiz_answers add column if not exists score_delta integer not null default 0;
alter table public.quiz_answers add column if not exists xp_delta integer not null default 0;
alter table public.quiz_answers add column if not exists explanation_snapshot text;

create index if not exists idx_quiz_modules_slug on public.quiz_modules(slug);
create index if not exists idx_quiz_levels_module_number on public.quiz_levels(module_id, level_number);
create index if not exists idx_quiz_questions_level_order on public.quiz_questions(level_id, order_index);
create index if not exists idx_quiz_attempts_user_started on public.quiz_attempts(user_id, started_at desc);
create index if not exists idx_quiz_answers_attempt on public.quiz_answers(attempt_id);
create index if not exists idx_quiz_progress_user_level on public.quiz_progress(user_id, level_id);

-- Prevent duplicate active quiz attempts for same user+level
create unique index if not exists uq_active_quiz_attempt_per_user_level
  on public.quiz_attempts (user_id, level_id)
  where status = 'active';
