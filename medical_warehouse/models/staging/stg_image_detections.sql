WITH source AS (
    SELECT * FROM {{ source('raw', 'image_detections') }}
)

SELECT
    message_id,
    channel_name,
    detected_classes,
    confidence_score,
    image_category
FROM source
