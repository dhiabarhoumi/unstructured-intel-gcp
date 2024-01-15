-- Hacker News stories from the last 7 days
-- Retrieves titles and text content for semantic analysis
SELECT 
    id,
    time,
    title,
    text,
    by AS author,
    score,
    descendants AS comment_count,
    url
FROM `bigquery-public-data.hacker_news.stories`
WHERE time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND (title IS NOT NULL OR text IS NOT NULL)
    AND deleted IS NULL
ORDER BY time DESC
LIMIT 100000;
