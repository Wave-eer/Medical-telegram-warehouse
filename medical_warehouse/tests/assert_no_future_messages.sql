-- Custom test to assert that there are no messages dated in the future.
-- Any message with message_date in the future will fail this test.
SELECT
    message_id,
    message_date
FROM {{ ref('stg_telegram_messages') }}
WHERE message_date > CURRENT_TIMESTAMP
