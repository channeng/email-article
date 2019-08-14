# Describe columns for a given table
PRAGMA table_info(ticker_recommendation);
# Show all tables in DB
.tables
# Delete row from user table where user id is 4
DELETE FROM user WHERE id = 4;
# Set column 'active' for all rows in user table to be True
UPDATE user SET active = 1;
# Set column 'confirmed_at' for all rows in user table to be of given date
UPDATE user SET confirmed_at = '2019-06-01 10:00:00';
# Delete ticker of given name
UPDATE ticker SET is_deleted = 1 WHERE name = "OV8.SI";
# Get all ticker recommendations
SELECT tr.time_created, name, closing_date, closing_price, recommendation
FROM ticker_recommendation AS tr
LEFT JOIN ticker ON ticker.id = tr.ticker_id
WHERE name = "CWEB"
ORDER BY closing_date;
# Get latest recommendation for a given ticker
SELECT
    ticker_recommendation.time_created,
    ticker.name,
    ticker.id,
    closing_date,
    recommendation,
    is_strong
FROM ticker_recommendation
JOIN ticker ON ticker.id = ticker_recommendation.ticker_id
WHERE name = "FB"
ORDER BY closing_date DESC
LIMIT 1;
# Get latest recommendations for a given user
SELECT
    ticker_id,
    MAX(recommendation) AS recommendation,
    MAX(is_strong) AS is_strong
FROM (
    SELECT *
    FROM ticker_recommendation
    INNER JOIN (
        SELECT ticker_id
        FROM ticker_user
        WHERE user_id = 1
        AND is_deleted = 0
        GROUP BY 1
    ) USING (ticker_id)
    WHERE DATE(time_created) = (
        SELECT MAX(DATE(time_created))
        FROM ticker_recommendation
    )
)
GROUP BY ticker_id;

# Get users -> ticker signups
SELECT
    user.username,
    ticker.id,
    ticker.name,
    ticker.full_name,
    ticker_user.time_created
FROM ticker_user
LEFT JOIN user ON user.id = ticker_user.user_id
LEFT JOIN ticker on ticker.id = ticker_user.ticker_id
WHERE ticker_user.is_deleted=0
AND ticker.is_deleted=0
ORDER BY ticker_user.id;

# Quit SQLite3
.quit

# Get ticker recommendations
WITH live_tickers AS (
    SELECT
        ticker.id AS ticker_id,
        ticker.name AS ticker_name
    FROM ticker_user
    LEFT JOIN ticker
    ON ticker_user.ticker_id = ticker.id
    WHERE ticker_user.is_deleted = 0
    AND ticker.is_deleted = 0
    GROUP BY 1,2
)
, latest_updated AS (
    SELECT MAX(DATE(ticker_recommendation.time_created)) last_updated
    FROM ticker_recommendation
    LEFT JOIN ticker ON ticker.id = ticker_recommendation.ticker_id
    -- Exclude non-US stocks
    WHERE ticker.name NOT LIKE '%.%'
)
, latest_recommendations AS (
    SELECT
        ticker_id,
        recommendation,
        closing_date,
        time_created AS time_recommended
    FROM ticker_recommendation
    WHERE DATE(time_created) = (SELECT last_updated FROM latest_updated)
)

SELECT closing_date, ticker_id, ticker_name, recommendation, time_recommended
FROM live_tickers
LEFT JOIN latest_recommendations USING(ticker_id)
-- Exclude non-US stocks
WHERE ticker_name NOT LIKE '%.%'
ORDER BY ticker_name;
