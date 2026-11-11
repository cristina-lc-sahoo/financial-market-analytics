
{{ config(materialized='table') }}

SELECT
    ticker,
    trade_date,

    COUNT(*) AS record_count,

    ROUND(AVG(close_price), 2) AS average_close,
    ROUND(MAX(high_price), 2) AS highest_price,
    ROUND(MIN(low_price), 2) AS lowest_price,

    ROUND(SUM(volume), 2) AS total_volume,
    SUM(transactions) AS total_transactions,

    ROUND(AVG(vwap), 2) AS average_vwap

FROM {{ ref('stg_stock_prices') }}

GROUP BY
    ticker,
    trade_date

