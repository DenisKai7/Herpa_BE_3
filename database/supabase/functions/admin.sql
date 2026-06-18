create or replace function public.admin_dashboard_overview()
returns table(
  total_users bigint,
  total_messages bigint,
  total_chats bigint,
  active_users_today bigint,
  messages_today bigint,
  total_recommendations bigint,
  total_attachments bigint,
  total_quiz_attempts bigint,
  error_rate double precision,
  average_latency_ms double precision
)
language sql security definer set search_path=public as $$
 select
  (select count(*) from profiles where account_status<>'deleted'),
  (select count(*) from chat_messages),
  (select count(*) from chats where deleted_at is null),
  (select count(*) from profiles where last_active_at>=current_date),
  (select count(*) from chat_messages where created_at>=current_date),
  (select count(*) from recommendation_sessions),
  (select count(*) from attachments where deleted_at is null),
  (select count(*) from quiz_attempts where deleted_at is null),
  coalesce((select 100.0*count(*) filter(where not success)/nullif(count(*),0) from feature_usage_events),0),
  coalesce((select avg(latency_ms) from feature_usage_events where latency_ms is not null),0);
$$;

create or replace function public.admin_storage_summary()
returns jsonb language sql security definer set search_path=public as $$
 with active as (
   select bucket,size_bytes from storage_objects where deleted_at is null
 ), bucket_totals as (
   select bucket,sum(size_bytes) as bytes from active group by bucket
 )
 select jsonb_build_object(
   'total_bytes',coalesce((select sum(size_bytes) from active),0),
   'objects',(select count(*) from active),
   'buckets',coalesce((select jsonb_object_agg(bucket,bytes) from bucket_totals),'{}'::jsonb)
 );
$$;

grant execute on function public.admin_dashboard_overview() to service_role;
grant execute on function public.admin_storage_summary() to service_role;
