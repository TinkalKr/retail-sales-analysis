-- =====================================================================
-- Retail Sales Analysis | SQLite
-- Table: sales(transaction_id, customer_id, category, item,
--              price_per_unit, quantity, total_spent, payment_method,
--              location, transaction_date, discount_applied,
--              year, month, year_month)
-- Each "-- name:" line labels a query so 03_run_analysis.py can run it
-- and save the result to results/<name>.csv
-- =====================================================================


-- name: q1_top_10_products_by_revenue
-- Business question: Which products bring in the most money?
SELECT
    item,
    category,
    ROUND(SUM(total_spent), 2) AS revenue,
    SUM(quantity)              AS units_sold,
    COUNT(*)                   AS orders
FROM sales
GROUP BY item, category
ORDER BY revenue DESC
LIMIT 10;


-- name: q2_monthly_sales_trend
-- Business question: How do sales change month to month?
SELECT
    year_month,
    ROUND(SUM(total_spent), 2) AS revenue,
    COUNT(*)                   AS orders,
    SUM(quantity)              AS units_sold
FROM sales
GROUP BY year_month
ORDER BY year_month;


-- name: q3_sales_by_category
-- Business question: Which categories drive the business?
-- Uses a window function to show each category's share of total revenue.
SELECT
    category,
    ROUND(SUM(total_spent), 2)                                  AS revenue,
    COUNT(*)                                                    AS orders,
    ROUND(AVG(total_spent), 2)                                  AS avg_order_value,
    ROUND(100.0 * SUM(total_spent) / SUM(SUM(total_spent)) OVER (), 2) AS revenue_share_pct
FROM sales
GROUP BY category
ORDER BY revenue DESC;


-- name: q4_top_5_customers
-- Business question: Who are the most valuable customers?
SELECT
    customer_id,
    ROUND(SUM(total_spent), 2) AS lifetime_spend,
    COUNT(*)                   AS orders,
    ROUND(AVG(total_spent), 2) AS avg_order_value,
    MIN(transaction_date)      AS first_purchase,
    MAX(transaction_date)      AS last_purchase
FROM sales
GROUP BY customer_id
ORDER BY lifetime_spend DESC
LIMIT 5;


-- name: q5_average_order_value
-- Business question: How much does a typical order bring in?
-- Overall, then split by sales channel.
SELECT
    'All orders'               AS segment,
    COUNT(*)                   AS orders,
    ROUND(AVG(total_spent), 2) AS avg_order_value
FROM sales
UNION ALL
SELECT
    location                   AS segment,
    COUNT(*)                   AS orders,
    ROUND(AVG(total_spent), 2) AS avg_order_value
FROM sales
GROUP BY location;


-- name: q6_bottom_10_products_by_revenue
-- Business question: Which products sell the least (candidates to
-- discontinue, discount or promote)?
SELECT
    item,
    category,
    ROUND(SUM(total_spent), 2) AS revenue,
    SUM(quantity)              AS units_sold,
    COUNT(*)                   AS orders
FROM sales
GROUP BY item, category
ORDER BY revenue ASC
LIMIT 10;


-- ---------------------------------------------------------------------
-- BONUS QUERIES
-- ---------------------------------------------------------------------

-- name: q7_yearly_revenue_growth
-- Business question: Is the business growing year over year?
-- Window function LAG() compares each year with the previous one.
-- Note: the data ends on 2025-01-18, so 2025 is a partial year and is
-- excluded; comparing it with full years would be misleading.
WITH yearly AS (
    SELECT year, ROUND(SUM(total_spent), 2) AS revenue, COUNT(*) AS orders
    FROM sales
    WHERE year < 2025
    GROUP BY year
)
SELECT
    year,
    revenue,
    orders,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year))
          / LAG(revenue) OVER (ORDER BY year), 2) AS growth_pct
FROM yearly
ORDER BY year;


-- name: q8_discount_impact
-- Business question: Do discounted orders spend more or less?
SELECT
    discount_applied,
    COUNT(*)                   AS orders,
    ROUND(AVG(total_spent), 2) AS avg_order_value,
    ROUND(AVG(quantity), 2)    AS avg_quantity
FROM sales
GROUP BY discount_applied
ORDER BY avg_order_value DESC;


-- name: q9_payment_method_mix
-- Business question: How do customers prefer to pay?
SELECT
    payment_method,
    COUNT(*)                                             AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)   AS order_share_pct,
    ROUND(SUM(total_spent), 2)                           AS revenue
FROM sales
GROUP BY payment_method
ORDER BY orders DESC;
