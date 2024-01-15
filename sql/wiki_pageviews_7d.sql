-- Wikipedia pageviews for English articles in the last 7 days
-- Identifies trending topics and public interest
SELECT 
    datehour,
    title,
    views,
    wiki
FROM `bigquery-public-data.wikipedia.pageviews_2024`
WHERE wiki = 'en'
    AND datehour >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND title NOT LIKE 'Special:%'
    AND title NOT LIKE 'File:%'
    AND title NOT LIKE 'Talk:%'
    AND title NOT LIKE 'User:%'
    AND title NOT LIKE 'Wikipedia:%'
    AND views > 100  -- Filter low-traffic pages
ORDER BY views DESC
LIMIT 500000;
