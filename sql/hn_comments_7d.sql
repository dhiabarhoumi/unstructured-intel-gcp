-- Hacker News comments from the last 7 days
-- Captures community discussions and sentiment
SELECT 
    id,
    time,
    parent,
    text,
    by AS author,
    ranking
FROM `bigquery-public-data.hacker_news.comments`
WHERE time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND text IS NOT NULL
    AND deleted IS NULL
    AND LENGTH(text) > 50  -- Filter out very short comments
ORDER BY time DESC
LIMIT 200000;
