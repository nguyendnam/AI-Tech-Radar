-- Fresh installation: delete the old project tables in Supabase first.
-- Paste this ENTIRE file into SQL Editor and Run once. No migration chain.
begin;

create table public.radar_items (
    id uuid primary key default gen_random_uuid(),
    source_platform text not null check (source_platform in ('rss', 'hn', 'github', 'huggingface', 'pypi')),
    external_id text not null check (length(external_id) > 0),
    item_type text not null check (item_type in ('NEWS', 'PAPER', 'AI_MODEL', 'DEV_TOOL', 'GITHUB_REPO', 'RELEASE', 'LANGUAGE', 'FRAMEWORK', 'PACKAGE', 'SECURITY', 'OTHER')),
    name text,
    title text not null check (length(title) > 0),
    description text,
    url text not null unique check (url ~ '^https?://'),
    category text,
    relevance_score numeric(4,2) not null default 0 check (relevance_score between 0 and 10),
    novelty_score numeric(4,2) not null default 0 check (novelty_score between 0 and 10),
    quality_score numeric(4,2) not null default 0 check (quality_score between 0 and 10),
    momentum_score numeric(4,2) not null default 0 check (momentum_score between 0 and 10),
    importance_score numeric(4,2) not null default 0 check (importance_score between 0 and 10),
    final_score numeric(4,2) not null default 0 check (final_score between 0 and 10),
    summary text,
    why_it_matters text,
    radar_status text not null default 'WATCH' check (radar_status in ('WATCH', 'ASSESS', 'TRIAL', 'ADOPT')),
    metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
    published_at timestamptz,
    discovered_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    sent_at timestamptz,
    saved boolean not null default false,
    unique (source_platform, external_id)
);

create index radar_items_unsent on public.radar_items (final_score desc, discovered_at)
    where sent_at is null;
create index radar_items_cleanup on public.radar_items (discovered_at, final_score)
    where saved = false and radar_status <> 'ADOPT';
create index radar_items_type on public.radar_items (item_type, final_score desc);

alter table public.radar_items enable row level security;
revoke all on table public.radar_items from anon, authenticated;
grant usage on schema public to service_role;
grant select, insert, update, delete on table public.radar_items to service_role;

commit;
