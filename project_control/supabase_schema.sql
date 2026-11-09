create extension if not exists pgcrypto;
create extension if not exists citext;

create table if not exists public.provinces (
  id uuid primary key default gen_random_uuid(),
  name citext not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  province_id uuid not null references public.provinces(id) on delete cascade,
  name citext not null,
  created_at timestamptz not null default now(),
  unique (province_id, name)
);

create table if not exists public.project_uploads (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  project_year text not null,
  content_type text not null,
  file_name text not null,
  sheet_name text,
  record_count integer not null default 0,
  storage_path text not null,
  action text not null default 'Uploaded',
  uploaded_at timestamptz not null default now()
);

create table if not exists public.project_dataset_rows (
  id uuid primary key default gen_random_uuid(),
  upload_id uuid not null unique references public.project_uploads(id) on delete cascade,
  rows jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

-- Keeps Project Control province access separate from the shared accounts table.
create table if not exists public.project_province_access (
  account_id uuid not null references public.accounts(id) on delete cascade,
  province_id uuid not null references public.provinces(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (account_id, province_id)
);

create index if not exists idx_projects_province on public.projects(province_id);
create index if not exists idx_uploads_project on public.project_uploads(project_id);
create index if not exists idx_uploads_date on public.project_uploads(uploaded_at desc);

alter table public.project_uploads alter column project_id set not null;

alter table public.provinces enable row level security;
alter table public.projects enable row level security;
alter table public.project_uploads enable row level security;
alter table public.project_dataset_rows enable row level security;
alter table public.project_province_access enable row level security;

insert into storage.buckets (id, name, public)
values ('project-monitoring-files', 'project-monitoring-files', false)
on conflict (id) do nothing;

-- The Streamlit server uses SUPABASE_SERVICE_ROLE_KEY from its private secrets.
-- Do not expose that key in browser code or commit it to the repository.
