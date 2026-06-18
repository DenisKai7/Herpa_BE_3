create extension if not exists pgcrypto;

do $$ begin
  create type public.application_role as enum ('admin','user');
exception when duplicate_object then null; end $$;
do $$ begin
  create type public.persona_type as enum ('umum','pelajar','peneliti','tenaga_medis');
exception when duplicate_object then null; end $$;
do $$ begin
  create type public.account_status as enum ('active','suspended','deleted');
exception when duplicate_object then null; end $$;
do $$ begin
  create type public.message_role as enum ('user','ai','assistant','system','tool');
exception when duplicate_object then null; end $$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  username text unique,
  full_name text,
  instansi text,
  provinsi text,
  kota text,
  avatar_object_key text,
  application_role public.application_role not null default 'user',
  persona public.persona_type not null default 'umum',
  account_status public.account_status not null default 'active',
  storage_quota_bytes bigint not null default 104857600 check (storage_quota_bytes >= 0),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), last_active_at timestamptz
);
create table if not exists public.user_preferences (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  language text not null default 'id', theme text not null default 'system', preferences jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
create table if not exists public.chats (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null default 'Percakapan baru', is_pinned boolean not null default false, is_public boolean not null default false, is_archived boolean not null default false,
  persona_snapshot public.persona_type not null default 'umum', last_message_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), deleted_at timestamptz
);
create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(), chat_id uuid not null references public.chats(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade, role public.message_role not null,
  content text not null, status text not null default 'completed', model_name text, grounding_status text,
  confidence real check (confidence between 0 and 1), token_input integer, token_output integer, latency_ms integer,
  metadata jsonb not null default '{}'::jsonb, quiz_data jsonb, file_context text, created_at timestamptz not null default now()
);
create table if not exists public.message_sources (
  id uuid primary key default gen_random_uuid(), message_id uuid not null references public.chat_messages(id) on delete cascade,
  source_type text not null, source_id text, title text, url text, evidence_level text, metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create table if not exists public.attachments (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
  chat_id uuid references public.chats(id) on delete set null, message_id uuid references public.chat_messages(id) on delete set null,
  bucket text not null, object_key text not null unique, filename text not null, mime_type text not null,
  size_bytes bigint not null check (size_bytes >= 0), processing_status text not null default 'uploading', verification_status text not null default 'pending',
  confidence real not null default 0 check(confidence between 0 and 1), extracted_text text, extraction_metadata jsonb not null default '{}'::jsonb, quiz_data jsonb, file_context text, created_at timestamptz not null default now(), deleted_at timestamptz
);
create table if not exists public.attachment_jobs (
  id uuid primary key default gen_random_uuid(), attachment_id uuid not null references public.attachments(id) on delete cascade,
  status text not null default 'queued', attempts integer not null default 0, error_code text, error_message text,
  started_at timestamptz, finished_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.shared_chats (
  id uuid primary key default gen_random_uuid(), chat_id uuid not null references public.chats(id) on delete cascade,
  owner_id uuid not null references public.profiles(id) on delete cascade, share_token_hash text not null unique,
  is_active boolean not null default true, expires_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.recommendation_sessions (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
  input jsonb not null, status text not null default 'completed', red_flags jsonb not null default '[]'::jsonb,
  limitations jsonb not null default '[]'::jsonb, created_at timestamptz not null default now()
);
create table if not exists public.recommendation_results (
  id uuid primary key default gen_random_uuid(), session_id uuid not null references public.recommendation_sessions(id) on delete cascade,
  plant_id text, local_name text, scientific_name text, relevance_score real, result jsonb not null, created_at timestamptz not null default now()
);
create table if not exists public.quiz_subjects (
  id uuid primary key default gen_random_uuid(), slug text not null unique, title text not null, description text, sort_order integer not null default 0, is_active boolean not null default true
);
create table if not exists public.quiz_modules (
  id uuid primary key default gen_random_uuid(), subject_id uuid not null references public.quiz_subjects(id) on delete cascade,
  slug text not null unique, title text not null, description text, sort_order integer not null default 0, is_active boolean not null default true
);
create table if not exists public.quiz_levels (
  id uuid primary key default gen_random_uuid(), module_id uuid not null references public.quiz_modules(id) on delete cascade,
  level_number integer not null check(level_number between 1 and 5), title text not null, passing_score integer not null default 70,
  xp_reward integer not null default 25, unique(module_id,level_number)
);
create table if not exists public.quiz_questions (
  id uuid primary key default gen_random_uuid(), level_id uuid not null references public.quiz_levels(id) on delete cascade,
  question_type text not null, prompt text not null, explanation text, correct_answer jsonb not null,
  difficulty integer not null default 1, metadata jsonb not null default '{}'::jsonb, is_active boolean not null default true
);
create table if not exists public.quiz_question_options (
  id uuid primary key default gen_random_uuid(), question_id uuid not null references public.quiz_questions(id) on delete cascade,
  option_key text not null, label text not null, is_correct boolean not null default false, sort_order integer not null default 0
);
create table if not exists public.quiz_attempts (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
  level_id uuid not null references public.quiz_levels(id), status text not null default 'started', seed bigint,
  score integer, total_questions integer, accuracy real, correct integer, incorrect integer, skipped integer,
  xp_earned integer not null default 0, started_at timestamptz not null default now(), completed_at timestamptz, deleted_at timestamptz
);
create table if not exists public.quiz_answers (
  id uuid primary key default gen_random_uuid(), attempt_id uuid not null references public.quiz_attempts(id) on delete cascade,
  question_id uuid not null references public.quiz_questions(id), answer jsonb, is_correct boolean, is_skipped boolean not null default false,
  duration_ms integer, created_at timestamptz not null default now(), unique(attempt_id,question_id)
);
create table if not exists public.quiz_progress (
  user_id uuid not null references public.profiles(id) on delete cascade, level_id uuid not null references public.quiz_levels(id) on delete cascade,
  unlocked boolean not null default false, completed boolean not null default false, best_accuracy real not null default 0,
  attempts_count integer not null default 0, updated_at timestamptz not null default now(), primary key(user_id,level_id)
);
create table if not exists public.user_xp (user_id uuid primary key references public.profiles(id) on delete cascade, xp bigint not null default 0, updated_at timestamptz not null default now());
create table if not exists public.user_streaks (user_id uuid primary key references public.profiles(id) on delete cascade, current_streak integer not null default 0, longest_streak integer not null default 0, last_activity_date date, updated_at timestamptz not null default now());
create table if not exists public.badges (id uuid primary key default gen_random_uuid(), slug text unique not null, title text not null, description text, criteria jsonb not null default '{}'::jsonb);
create table if not exists public.user_badges (user_id uuid references public.profiles(id) on delete cascade, badge_id uuid references public.badges(id) on delete cascade, awarded_at timestamptz not null default now(), primary key(user_id,badge_id));
create table if not exists public.feature_usage_events (
 id bigint generated always as identity primary key, user_id uuid references public.profiles(id) on delete set null, event_name text not null,
 persona public.persona_type, success boolean not null default true, latency_ms integer, metadata jsonb not null default '{}'::jsonb, quiz_data jsonb, file_context text, created_at timestamptz not null default now()
);
create table if not exists public.model_usage_events (
 id bigint generated always as identity primary key, user_id uuid references public.profiles(id) on delete set null, request_id text,
 model_name text not null, input_tokens integer, output_tokens integer, latency_ms integer, success boolean not null default true,
 error_code text, created_at timestamptz not null default now()
);
create table if not exists public.storage_objects (
 id uuid primary key default gen_random_uuid(), user_id uuid references public.profiles(id) on delete cascade, bucket text not null,
 object_key text not null unique, size_bytes bigint not null, object_type text not null, created_at timestamptz not null default now(), deleted_at timestamptz
);
create table if not exists public.admin_audit_logs (
 id bigint generated always as identity primary key, admin_id uuid references public.profiles(id) on delete set null,
 action text not null, target_type text, target_id text, before_data jsonb, after_data jsonb, request_id text, created_at timestamptz not null default now()
);
create table if not exists public.system_health_logs (
 id bigint generated always as identity primary key, service text not null, status text not null, latency_ms integer, details jsonb not null default '{}'::jsonb, checked_at timestamptz not null default now()
);

create index if not exists chats_user_updated_idx on public.chats(user_id, updated_at desc) where deleted_at is null;
create index if not exists messages_chat_created_idx on public.chat_messages(chat_id, created_at);
create index if not exists attachments_user_idx on public.attachments(user_id, created_at desc) where deleted_at is null;
create index if not exists quiz_attempts_user_idx on public.quiz_attempts(user_id, started_at desc) where deleted_at is null;
create index if not exists feature_usage_created_idx on public.feature_usage_events(created_at desc, event_name);
create index if not exists model_usage_created_idx on public.model_usage_events(created_at desc, model_name);
