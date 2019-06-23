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
# Quit SQLite3
.quit
