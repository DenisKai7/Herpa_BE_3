-- Service-role bypasses RLS. Browser clients remain owner-scoped.
alter table public.profiles enable row level security;
alter table public.user_preferences enable row level security;
alter table public.chats enable row level security;
alter table public.chat_messages enable row level security;
alter table public.message_sources enable row level security;
alter table public.attachments enable row level security;
alter table public.shared_chats enable row level security;
alter table public.recommendation_sessions enable row level security;
alter table public.recommendation_results enable row level security;
alter table public.quiz_attempts enable row level security;
alter table public.quiz_answers enable row level security;
alter table public.quiz_progress enable row level security;
alter table public.user_xp enable row level security;
alter table public.user_streaks enable row level security;
alter table public.user_badges enable row level security;
alter table public.storage_objects enable row level security;

create or replace function public.is_admin() returns boolean language sql stable security definer set search_path=public as $$
 select exists(select 1 from public.profiles where id=auth.uid() and application_role='admin' and account_status='active');
$$;

create or replace function public.current_application_role() returns public.application_role language sql stable security definer set search_path=public as $$ select application_role from public.profiles where id=auth.uid(); $$;
create or replace function public.current_account_status() returns public.account_status language sql stable security definer set search_path=public as $$ select account_status from public.profiles where id=auth.uid(); $$;

create policy profiles_read_self on public.profiles for select using(id=auth.uid() or public.is_admin());
create policy profiles_update_self on public.profiles for update using(id=auth.uid()) with check(id=auth.uid() and application_role=public.current_application_role() and account_status=public.current_account_status());
create policy prefs_owner_all on public.user_preferences for all using(user_id=auth.uid()) with check(user_id=auth.uid());
create policy chats_owner_all on public.chats for all using(user_id=auth.uid()) with check(user_id=auth.uid());
create policy messages_owner_read on public.chat_messages for select using(user_id=auth.uid());
create policy messages_owner_insert on public.chat_messages for insert with check(user_id=auth.uid() and exists(select 1 from public.chats c where c.id=chat_id and c.user_id=auth.uid()));
create policy sources_owner_read on public.message_sources for select using(exists(select 1 from public.chat_messages m where m.id=message_id and m.user_id=auth.uid()));
create policy attachments_owner_all on public.attachments for all using(user_id=auth.uid()) with check(user_id=auth.uid());
create policy shared_owner_all on public.shared_chats for all using(owner_id=auth.uid()) with check(owner_id=auth.uid());
create policy rec_sessions_owner_all on public.recommendation_sessions for all using(user_id=auth.uid()) with check(user_id=auth.uid());
create policy rec_results_owner_read on public.recommendation_results for select using(exists(select 1 from public.recommendation_sessions s where s.id=session_id and s.user_id=auth.uid()));
create policy attempts_owner_all on public.quiz_attempts for all using(user_id=auth.uid()) with check(user_id=auth.uid());
create policy answers_owner_all on public.quiz_answers for all using(exists(select 1 from public.quiz_attempts a where a.id=attempt_id and a.user_id=auth.uid())) with check(exists(select 1 from public.quiz_attempts a where a.id=attempt_id and a.user_id=auth.uid()));
create policy progress_owner_all on public.quiz_progress for all using(user_id=auth.uid()) with check(user_id=auth.uid());
create policy xp_owner_read on public.user_xp for select using(user_id=auth.uid());
create policy streak_owner_read on public.user_streaks for select using(user_id=auth.uid());
create policy badges_owner_read on public.user_badges for select using(user_id=auth.uid());
create policy storage_owner_read on public.storage_objects for select using(user_id=auth.uid() or public.is_admin());
