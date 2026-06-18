create or replace function public.set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

create or replace function public.handle_new_user() returns trigger language plpgsql security definer set search_path=public as $$
begin
  insert into public.profiles(id,email,username,full_name)
  values(new.id,new.email,new.raw_user_meta_data->>'username',coalesce(new.raw_user_meta_data->>'nama',new.raw_user_meta_data->>'full_name'))
  on conflict(id) do nothing;
  insert into public.user_xp(user_id) values(new.id) on conflict do nothing;
  insert into public.user_streaks(user_id) values(new.id) on conflict do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute procedure public.handle_new_user();

do $$ begin
  create trigger profiles_updated_at before update on public.profiles for each row execute function public.set_updated_at();
exception when duplicate_object then null; end $$;
do $$ begin
  create trigger chats_updated_at before update on public.chats for each row execute function public.set_updated_at();
exception when duplicate_object then null; end $$;
