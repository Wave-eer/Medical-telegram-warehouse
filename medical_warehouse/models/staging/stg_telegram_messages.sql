WITH source AS (
    SELECT * FROM {{ source('raw', 'telegram_messages') }}
),

cleaned AS (
    SELECT
        message_id,
        channel_name,
        -- Clean channel names and assign category tags for marts mapping
        CASE 
            WHEN channel_name = 'CheMed Telegram Channel' THEN 'Medical'
            WHEN channel_name = 'Lobelia Cosmetics' THEN 'Cosmetics'
            WHEN channel_name = 'Tikvah Pharma' THEN 'Pharmaceutical'
            ELSE 'Other'
        END AS channel_type,
        message_date::timestamp with time zone AS message_date,
        COALESCE(message_text, '') AS message_text,
        COALESCE(has_media, FALSE) AS has_media,
        image_path,
        COALESCE(views, 0) AS views,
        COALESCE(forwards, 0) AS forwards
    FROM source
    WHERE message_id IS NOT NULL
      -- Filter out empty spam or corrupted records
      AND message_date IS NOT NULL
)

SELECT
    *,
    LENGTH(message_text) AS message_length,
    CASE 
        WHEN has_media = TRUE AND image_path IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS has_image
FROM cleaned
