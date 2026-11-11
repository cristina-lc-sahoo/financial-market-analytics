
{{ config(materialized='view') }}

SELECT
    CAST(ticker AS VARCHAR) AS ticker,
    CAST(ingestion_timestamp AS VARCHAR) AS ingestion_timestamp,
    CAST(source AS VARCHAR) AS source,
    CAST(source_file AS VARCHAR) AS source_file,

    CAST(volume AS DOUBLE) AS volume,
    CAST(vwap AS DOUBLE) AS vwap,
    CAST(open AS DOUBLE) AS open_price,
    CAST(close AS DOUBLE) AS close_price,
    CAST(high AS DOUBLE) AS high_price,
    CAST(low AS DOUBLE) AS low_price,

    CAST(timestamp_ms AS BIGINT) AS timestamp_ms,
    CAST(transactions AS BIGINT) AS transactions,

    CAST(
        from_unixtime(CAST(timestamp_ms AS DOUBLE) / 1000.0)
        AS DATE
    ) AS trade_date

FROM {{ source('market_data', 'market_data_processed') }}

WHERE ticker IS NOT NULL
  AND timestamp_ms IS NOT NULL

