WITH messages AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
)

SELECT
    m.message_id,
    MD5(m.channel_name) AS channel_key,
    CAST(TO_CHAR(m.message_date, 'YYYYMMDD') AS INTEGER) AS date_key,
    m.message_text,
    m.message_length,
    m.views AS view_count,
    m.forwards AS forward_count,
    m.has_image
FROM messages m
