-- GitHub README files sample from popular repositories
-- Captures project documentation and technical descriptions
SELECT 
    c.id,
    c.repo_name,
    c.path,
    c.size,
    c.content,
    l.language
FROM `bigquery-public-data.github_repos.contents` c
LEFT JOIN (
    SELECT repo_name, ARRAY_AGG(language.name ORDER BY language.bytes DESC LIMIT 1)[OFFSET(0)] as language
    FROM `bigquery-public-data.github_repos.languages`, UNNEST(language) as language
    GROUP BY repo_name
) l ON c.repo_name = l.repo_name
WHERE LOWER(c.path) LIKE '%readme%'
    AND c.size BETWEEN 100 AND 50000
    AND c.content IS NOT NULL
    AND l.language IN ('Python', 'JavaScript', 'Java', 'Go', 'TypeScript', 'Rust', 'C++')
LIMIT 50000;
