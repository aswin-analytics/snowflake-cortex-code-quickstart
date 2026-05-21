--   │ # │ Query                        │ Purpose                                                                                             │
--   ├───┼──────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
--   │ 1 │ Daily Dollar Cost            │ Actual USD spend per day using rate sheet — the real cost, not just credits                          │
--   ├───┼──────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
--   │ 2 │ Daily Credit Consumption     │ Day-by-day CoCo credits (CLI + Snowsight) over last 30 days — spot trends                           │
--   ├───┼──────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
--   │ 3 │ Usage by User                │ Which users consume the most credits, request counts, token totals — for chargeback/limits          │
--   ├───┼──────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
--   │ 4 │ Weekly Trend + Forecast      │ 12-week history with a projected monthly cost based on recent average — budget planning             │
--   ├───┼──────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
--   │ 5 │ CoCo vs Other AI Services    │ Puts CoCo spending alongside Cortex Agents, AI_SERVICES, etc. as % of total — relative cost context │
--   ├───┼──────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
--   │ 6 │ Session-Level Detail         │ Individual CLI requests with tokens and credits — audit spikes or heavy sessions                    │
-- ============================================================
-- Cortex Code Usage & Spending Queries
-- Run these against SNOWFLAKE.ACCOUNT_USAGE and SNOWFLAKE.ORGANIZATION_USAGE
-- to track CoCo credit consumption and actual dollar costs.
-- Requires: ACCOUNTADMIN role (ORGADMIN for rate sheet access).
-- ============================================================


-- ============================================================
-- 1. Daily Cortex Code Dollar Cost (Last 30 Days)
--    Joins daily credit usage with the organization rate sheet to
--    calculate actual USD spend per day. This is the most accurate
--    way to see real cost on your account.
--    Rate: $2.00/credit (Business Critical, AWS US West 2).
-- ============================================================
SELECT
    m.usage_date,
    m.service_type,
    ROUND(SUM(m.credits_used), 4) AS credits_consumed,
    r.currency,
    ROUND(SUM(m.credits_used) * r.effective_rate, 2) AS cost_in_currency
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY m
LEFT JOIN (
    SELECT DISTINCT service_type, currency, effective_rate
    FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY
    WHERE service_type IN ('CORTEX_CODE_CLI', 'CORTEX_CODE_SNOWSIGHT')
) r ON m.service_type = r.service_type
WHERE m.service_type IN ('CORTEX_CODE_CLI', 'CORTEX_CODE_SNOWSIGHT')
  AND m.usage_date >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY m.usage_date, m.service_type, r.currency, r.effective_rate
ORDER BY m.usage_date DESC, m.service_type;


-- ============================================================
-- 2. Daily Cortex Code Credit Consumption (Last 30 Days)
--    Shows day-by-day credit usage for both CLI and Snowsight surfaces.
--    Use this to spot trends and estimate monthly burn rate.
-- ============================================================
SELECT
    usage_date,
    service_type,
    ROUND(SUM(credits_used), 4) AS credits_consumed
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE service_type IN ('CORTEX_CODE_CLI', 'CORTEX_CODE_SNOWSIGHT')
  AND usage_date >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY usage_date, service_type
ORDER BY usage_date DESC, service_type;


-- ============================================================
-- 3. Cortex Code CLI Usage by User (Last 30 Days)
--    Shows which users are consuming the most credits.
--    Useful for per-user limit planning and chargeback.
-- ============================================================
SELECT
    user_name,
    COUNT(*) AS request_count,
    ROUND(SUM(token_credits), 4) AS total_credits,
    SUM(tokens) AS total_tokens,
    MIN(usage_time) AS first_usage,
    MAX(usage_time) AS last_usage
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_CODE_CLI_USAGE_HISTORY
WHERE usage_time >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY user_name
ORDER BY total_credits DESC;


-- ============================================================
-- 4. Weekly Spending Trend with Forecast (Last 12 Weeks)
--    Shows weekly credit totals and a simple linear projection
--    for the next 4 weeks based on recent average.
-- ============================================================
WITH weekly_usage AS (
    SELECT
        DATE_TRUNC('WEEK', usage_date) AS week_start,
        ROUND(SUM(credits_used), 4) AS weekly_credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
    WHERE service_type IN ('CORTEX_CODE_CLI', 'CORTEX_CODE_SNOWSIGHT')
      AND usage_date >= DATEADD('week', -12, CURRENT_DATE())
    GROUP BY week_start
),
avg_usage AS (
    SELECT ROUND(AVG(weekly_credits), 4) AS avg_weekly_credits
    FROM weekly_usage
)
SELECT
    w.week_start,
    w.weekly_credits,
    a.avg_weekly_credits AS projected_weekly_rate,
    ROUND(a.avg_weekly_credits * 4, 4) AS projected_monthly_cost
FROM weekly_usage w
CROSS JOIN avg_usage a
ORDER BY w.week_start DESC;


-- ============================================================
-- 5. Cortex Code vs Other AI Services Cost Breakdown (Last 30 Days)
--    Puts CoCo spending in context alongside other Cortex AI services.
--    Helps admins understand relative cost of each AI feature.
-- ============================================================
SELECT
    service_type,
    ROUND(SUM(credits_used), 4) AS total_credits,
    ROUND(SUM(credits_used) * 100.0 / NULLIF(SUM(SUM(credits_used)) OVER (), 0), 1) AS pct_of_total_ai_spend
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE service_type IN (
    'AI_SERVICES',
    'CORTEX_AGENTS',
    'CORTEX_CODE_CLI',
    'CORTEX_CODE_SNOWSIGHT',
    'SNOWFLAKE_INTELLIGENCE'
)
AND usage_date >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY service_type
ORDER BY total_credits DESC;


-- ============================================================
-- 6. Detailed Session-Level CLI Usage (Last 7 Days)
--    Shows individual CoCo CLI requests with token counts and credits.
--    Useful for auditing heavy sessions or investigating spikes.
-- ============================================================
SELECT
    usage_time,
    user_name,
    request_id,
    tokens,
    ROUND(token_credits, 6) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_CODE_CLI_USAGE_HISTORY
WHERE usage_time >= DATEADD('day', -7, CURRENT_DATE())
ORDER BY usage_time DESC
LIMIT 100;
