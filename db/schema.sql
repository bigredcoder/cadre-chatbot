-- Cadence database (Supabase project "cadre-chatbot", us-west-1).
-- Applied 2026-09-23 as two migrations: create_chat_turns, schedule_30_day_retention.
-- One row per chat turn: the redacted exchange plus routing and cost metrics.
-- Personal emails and phone numbers are redacted in the app (app/transcripts.py) BEFORE insert.

create table public.chat_turns (
  id                bigint generated always as identity primary key,
  created_at        timestamptz not null default now(),
  session_id        text not null check (char_length(session_id) between 8 and 64),
  user_message      text not null check (char_length(user_message) <= 1000),
  assistant_message text check (char_length(assistant_message) <= 8000),
  topic             text,
  confidence        real,
  router            text check (router in ('jev','fallback','default')),
  asks_for_human    boolean,
  handoff           boolean,
  model_handoff     boolean,
  outcome           text not null check (outcome in ('answered','handoff','off_topic','error','turn_limit')),
  model             text,
  latency_ms        integer,
  input_tokens      integer,
  output_tokens     integer,
  cost_usd          numeric(12,8)
);
create index chat_turns_created_at_idx on public.chat_turns (created_at);
create index chat_turns_session_idx on public.chat_turns (session_id);

-- Least privilege: the app's public (publishable) key may INSERT only.
-- Verified 2026-09-23: GET, PATCH, and DELETE with that key all return 401.
alter table public.chat_turns enable row level security;
revoke all on public.chat_turns from anon, authenticated;
grant insert on public.chat_turns to anon;
create policy "app can insert turns" on public.chat_turns
  for insert to anon with check (true);

-- Retention: nightly delete of anything older than 30 days.
create extension if not exists pg_cron;
select cron.schedule(
  'delete-chat-turns-older-than-30-days',
  '17 3 * * *',
  $$delete from public.chat_turns where created_at < now() - interval '30 days'$$
);

-- Production design, NOT built (the handoff form is a demo and stores nothing):
-- create table public.leads (id, created_at, session_id, name, email, subject, message,
--   topic, idempotency_key unique, status) with insert-only RLS, and a CRM sync job.

-- Handy review queries (run in the Supabase SQL editor):
--   select topic, outcome, count(*) from chat_turns group by 1,2 order by 3 desc;  -- content gaps
--   select * from chat_turns where outcome in ('handoff','error') order by created_at desc;
