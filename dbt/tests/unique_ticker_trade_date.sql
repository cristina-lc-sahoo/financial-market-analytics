
SELECT
    ticker,
    trade_date,
    COUNT(*) AS duplicate_count

FROM {{ ref('stock_daily_summary') }}

GROUP BY
    ticker,
    trade_date

HAVING COUNT(*) > 1

