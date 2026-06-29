WITH messages AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),

channel_metrics AS (
    SELECT
        channel_name,
        channel_type,
        MIN(message_date) AS first_post_date,
        MAX(message_date) AS last_post_date,
        COUNT(message_id) AS total_posts,
        ROUND(AVG(views), 2) AS avg_views
    FROM messages
    GROUP BY channel_name, channel_type
)

SELECT
    MD5(channel_name) AS channel_key,
    channel_name,
    channel_type,
    first_post_date,
    last_post_date,
    total_posts,
    avg_views
FROM channel_metrics
