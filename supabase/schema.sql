-- UK government spending viz — Postgres schema for Supabase
-- Load from data/export/*.csv via COPY or Supabase dashboard import

create table if not exists regions (
  slug text primary key,
  name text not null,
  nation text not null,
  sort_order smallint not null
);

create table if not exists financial_years (
  label text primary key,
  start_year smallint not null,
  end_year smallint not null
);

create table if not exists cofog_functions (
  slug text primary key,
  name text not null,
  sort_order smallint not null
);

create table if not exists revenue_types (
  slug text primary key,
  name text not null,
  sort_order smallint not null
);

create table if not exists uk_fiscal_summary (
  id bigint generated always as identity primary key,
  fye text not null references financial_years (label),
  metric text not null,
  value_bn numeric(12, 2) not null,
  unique (fye, metric)
);

create table if not exists uk_spending_by_function (
  id bigint generated always as identity primary key,
  fye text not null references financial_years (label),
  function_slug text not null references cofog_functions (slug),
  function_name text not null,
  spend_bn numeric(12, 2) not null,
  pct_of_tme numeric(5, 1) not null,
  unique (fye, function_slug)
);

create table if not exists regional_fiscal (
  id bigint generated always as identity primary key,
  fye text not null references financial_years (label),
  region_slug text not null references regions (slug),
  region_name text not null,
  revenue_bn numeric(12, 2) not null,
  expenditure_identifiable_bn numeric(12, 2) not null,
  net_balance_bn numeric(12, 2) not null,
  revenue_per_head_gbp numeric(10, 2) not null,
  expenditure_per_head_gbp numeric(10, 2) not null,
  net_balance_per_head_gbp numeric(10, 2) not null,
  unique (fye, region_slug)
);

create table if not exists regional_revenue_by_type (
  id bigint generated always as identity primary key,
  fye text not null references financial_years (label),
  region_slug text not null references regions (slug),
  region_name text not null,
  revenue_type_slug text not null references revenue_types (slug),
  amount_bn numeric(12, 2) not null,
  pct_of_regional_total numeric(5, 1) not null,
  unique (fye, region_slug, revenue_type_slug)
);

create table if not exists pesa_tme_history (
  financial_year text primary key references financial_years (label),
  tme_bn numeric(12, 2) not null
);

create table if not exists pesa_spending_by_function_history (
  id bigint generated always as identity primary key,
  financial_year text not null references financial_years (label),
  function_slug text not null references cofog_functions (slug),
  function_name text not null,
  spend_bn numeric(12, 2) not null,
  pct_of_total numeric(5, 1) not null,
  unique (financial_year, function_slug)
);

-- Convenience views for the React app / API

create or replace view v_regional_balance_latest as
select
  r.name as region,
  r.nation,
  rf.revenue_bn,
  rf.expenditure_identifiable_bn,
  rf.net_balance_bn,
  rf.net_balance_per_head_gbp
from regional_fiscal rf
join regions r on r.slug = rf.region_slug
where rf.fye = (select max(fye) from regional_fiscal)
  and r.slug not in ('uk', 'england')
order by rf.net_balance_bn desc;

create or replace view v_uk_tme_trend as
select financial_year, tme_bn
from pesa_tme_history
order by financial_year;
