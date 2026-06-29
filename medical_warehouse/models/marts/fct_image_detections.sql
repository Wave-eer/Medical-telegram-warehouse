WITH detections AS (
    SELECT * FROM {{ ref('stg_image_detections') }}
),

messages AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
)

SELECT
    d.message_id,
    MD5(d.channel_name) AS channel_key,
    CAST(TO_CHAR(m.message_date, 'YYYYMMDD') AS INTEGER) AS date_key,
    d.detected_classes,
    d.confidence_score,
    d.image_category
FROM detections d
LEFT JOIN messages m 
    ON d.message_id = m.message_id 
    AND d.channel_name = m.channel_name
