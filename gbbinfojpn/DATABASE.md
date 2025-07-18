# supabase SQL Definition

## Category
```sql
create table public."Category" (
  id integer generated by default as identity not null,
  name character varying not null,
  display_order integer not null default 0,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint Category_pkey primary key (id),
  constraint Category_name_key unique (name)
) TABLESPACE pg_default;
```

## Country
```sql
create table public."Country" (
  iso_code integer not null,
  latitude numeric not null default '0'::numeric,
  longitude numeric not null default '0'::numeric,
  names jsonb not null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint Country_pkey primary key (iso_code),
  constraint Country_iso_code_key unique (iso_code),
  constraint Country_names_key unique (names)
) TABLESPACE pg_default;
```

## Participant
```sql
create table public."Participant" (
  id integer generated by default as identity not null,
  name character varying not null,
  year integer not null,
  iso_code integer not null,
  is_cancelled boolean not null default false,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  category integer not null,
  ticket_class character varying not null,
  constraint Participant_pkey primary key (id),
  constraint Participant_category_fkey foreign KEY (category) references "Category" (id) on delete CASCADE,
  constraint Participant_iso_code_fkey foreign KEY (iso_code) references "Country" (iso_code) on delete CASCADE,
  constraint Participant_year_fkey foreign KEY (year) references "Year" (year) on delete CASCADE
) TABLESPACE pg_default;
```

## ParticipantMember
```sql
create table public."ParticipantMember" (
  id bigint generated by default as identity not null,
  participant integer not null,
  name character varying not null,
  iso_code integer not null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint ParticipantMember_pkey primary key (id),
  constraint ParticipantMember_iso_code_fkey foreign KEY (iso_code) references "Country" (iso_code) on delete CASCADE,
  constraint ParticipantMember_participant_fkey foreign KEY (participant) references "Participant" (id) on delete CASCADE
) TABLESPACE pg_default;
```

## RankingResult
```sql
create table public."RankingResult" (
  id bigint generated by default as identity not null,
  year integer not null,
  category integer not null,
  round character varying null,
  participant integer not null,
  rank integer not null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint RankingResult_pkey primary key (id),
  constraint RankingResult_category_fkey foreign KEY (category) references "Category" (id) on delete CASCADE,
  constraint RankingResult_participant_fkey foreign KEY (participant) references "Participant" (id) on delete CASCADE,
  constraint RankingResult_year_fkey foreign KEY (year) references "Year" (year) on delete CASCADE
) TABLESPACE pg_default;
```

## TournamentResult
```sql
create table public."TournamentResult" (
  id integer generated by default as identity not null,
  year integer not null,
  category integer not null,
  round character varying not null,
  winner integer not null,
  loser integer not null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint TournamentResult_pkey primary key (id),
  constraint TournamentResult_category_fkey foreign KEY (category) references "Category" (id) on delete CASCADE,
  constraint TournamentResult_loser_fkey foreign KEY (loser) references "Participant" (id) on delete CASCADE,
  constraint TournamentResult_winner_fkey foreign KEY (winner) references "Participant" (id) on delete CASCADE,
  constraint TournamentResult_year_fkey foreign KEY (year) references "Year" (year) on delete CASCADE
) TABLESPACE pg_default;
```

## Year
```sql
create table public."Year" (
  year integer not null,
  starts_at timestamp with time zone null,
  ends_at timestamp with time zone null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  categories integer[] null,
  constraint Year_pkey primary key (year),
  constraint Year_year_key unique (year)
) TABLESPACE pg_default;
```

## test
原則使わない
databaseアプリで接続を確認するために使う
データが1行分入っている
```sql
create table public.test (
  id bigint generated by default as identity not null,
  created_at timestamp with time zone not null default now(),
  value text not null,
  constraint test_pkey primary key (id)
) TABLESPACE pg_default;
```
