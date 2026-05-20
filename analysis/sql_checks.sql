-- Borrower strategy root-cause SQL appendix
-- These examples are written in warehouse-style SQL for interview discussion.

-- 1. Cohort-level borrower health rollup.
with cohort_daily as (
  select
    segment_id,
    avg(delinquency_rate) as avg_delinquency_rate,
    avg(contact_rate) as avg_contact_rate,
    avg(application_completion_rate) as avg_application_completion_rate,
    avg(first_contact_resolution_rate) as avg_first_resolution_rate,
    avg(autopay_rate) as avg_autopay_rate
  from daily_borrower_metrics
  group by 1
)
select
  s.product,
  s.segment,
  c.avg_delinquency_rate,
  c.avg_contact_rate,
  c.avg_application_completion_rate,
  c.avg_first_resolution_rate,
  1 - c.avg_autopay_rate as autopay_gap
from cohort_daily c
join borrower_segments s
  on s.segment_id = c.segment_id
order by c.avg_delinquency_rate desc;

-- 2. Metric confidence gate before a recommendation is promoted.
select
  dataset,
  min(confidence) as lowest_confidence,
  sum(case when status = 'Fix' then 1 else 0 end) as fix_count,
  sum(case when status = 'Watch' then 1 else 0 end) as watch_count
from data_quality_checks
group by 1
having min(confidence) < 0.92
   or sum(case when status = 'Fix' then 1 else 0 end) > 0;

-- 3. Scenario economics for leadership tradeoff review.
select
  segment,
  scenario,
  forecast_delinquency_rate,
  annualized_value - operating_cost as modeled_net_value
from scenario_forecast
where scenario in ('Focused outreach', 'Full playbook')
order by modeled_net_value desc;
