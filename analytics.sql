-- 1. Top gainers and losers on the latest trading date
SELECT f.ticker, d.sector, f.close, f.daily_change_pct
FROM analytics.fact_stock_prices f
JOIN analytics.dim_stock d ON d.ticker = f.ticker
WHERE f.trade_date = (SELECT MAX(trade_date) FROM analytics.fact_stock_prices)
ORDER BY f.daily_change_pct DESC;

-- 2. Average percentage change by sector for the latest trading date
SELECT d.sector, COUNT(*) AS stocks, ROUND(AVG(f.daily_change_pct), 2) AS avg_change_pct
FROM analytics.fact_stock_prices f
JOIN analytics.dim_stock d ON d.ticker = f.ticker
WHERE f.trade_date = (SELECT MAX(trade_date) FROM analytics.fact_stock_prices)
GROUP BY d.sector
ORDER BY avg_change_pct DESC;

-- 3. 20-day Simple Moving Average (SMA) for AAPL using Window Functions
SELECT trade_date, close,
       ROUND(AVG(close) OVER (ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW), 2) AS sma_20
FROM analytics.fact_stock_prices
WHERE ticker = 'AAPL'
ORDER BY trade_date DESC
LIMIT 10;

-- 4. Quarterly average daily percentage change by sector
SELECT dt.year, dt.quarter, s.sector, ROUND(AVG(f.daily_change_pct), 2) AS avg_change_pct
FROM analytics.fact_stock_prices f
JOIN analytics.dim_date dt ON dt.full_date = f.trade_date
JOIN analytics.dim_stock s ON s.ticker = f.ticker
WHERE dt.is_trading_day
GROUP BY dt.year, dt.quarter, s.sector
ORDER BY dt.year, dt.quarter, avg_change_pct DESC;