-- Custom test to assert that views and forwards are non-negative.
-- Any records with negative values will fail this test.
SELECT
    message_id,
    views,
    forwards
FROM {{ ref('stg_telegram_messages') }}
WHERE views < 0 OR forwards < 0
