-- =====================================================================
-- Royal Point Capital: general_queries.sql
-- Exploratory analysis of the branch: is it successful, profitable and
-- realistic? Not part of the graded 01-02-03 scripts.
--
-- Run 01_create.sql, 02_load.sql and 03_demonstrate.sql first:
-- these queries reuse the views v_holdings and v_portfolio_value from 03.
-- All values are as of security.price_date (2026-10-16).
-- =====================================================================

PRAGMA foreign_keys = ON;


-- ---------------------------------------------------------------------
-- 1. SCALE: how big is the branch?
-- ---------------------------------------------------------------------

-- G1. Branch snapshot.
-- Looking for: AUM, number of relationships and average account size, to
-- compare with a real regional office of a mid-size wealth manager.
SELECT COUNT(*)                                           AS active_portfolios,
       (SELECT COUNT(DISTINCT po.client_id)
        FROM portfolio_owner po JOIN portfolio p ON p.portfolio_id = po.portfolio_id
        WHERE p.status = 'Active')                        AS active_clients,
       ROUND(SUM(total_value) / 1e6, 1)                   AS aum_musd,
       ROUND(AVG(total_value) / 1e6, 2)                   AS avg_portfolio_musd,
       ROUND(MAX(total_value) / 1e6, 1)                   AS largest_portfolio_musd,
       ROUND(100.0 * SUM(cash) / SUM(total_value), 1)     AS cash_pct_of_aum
FROM v_portfolio_value
WHERE status = 'Active';

-- G2. Median portfolio size (SQLite has no MEDIAN, so take the middle row).
-- Looking for: whether a few huge accounts pull the average up.
SELECT ROUND(total_value / 1e6, 2) AS median_portfolio_musd
FROM v_portfolio_value
WHERE status = 'Active'
ORDER BY total_value
LIMIT 1 OFFSET (SELECT COUNT(*) / 2 FROM v_portfolio_value WHERE status = 'Active');

-- G3. Concentration: share of AUM held by the 10 and 50 largest portfolios.
-- Looking for: key-client risk. If a handful of accounts hold most of the
-- money, losing one would hurt the branch badly.
WITH ranked AS (
    SELECT total_value,
           ROW_NUMBER() OVER (ORDER BY total_value DESC) AS rnk
    FROM v_portfolio_value
    WHERE status = 'Active'
)
SELECT ROUND(100.0 * SUM(CASE WHEN rnk <= 10 THEN total_value END) / SUM(total_value), 1) AS top10_pct_of_aum,
       ROUND(100.0 * SUM(CASE WHEN rnk <= 50 THEN total_value END) / SUM(total_value), 1) AS top50_pct_of_aum
FROM ranked;

-- G4. Account-size bands.
-- Looking for: the client mix (mass affluent vs high-net-worth vs ultra-high-net-worth).
SELECT CASE
           WHEN total_value <  1e6 THEN '1. under $1M'
           WHEN total_value <  5e6 THEN '2. $1M-5M'
           WHEN total_value < 25e6 THEN '3. $5M-25M'
           ELSE                         '4. $25M+'
       END                                           AS size_band,
       COUNT(*)                                      AS portfolios,
       ROUND(SUM(total_value) / 1e6, 1)              AS aum_musd,
       ROUND(100.0 * SUM(total_value)
             / (SELECT SUM(total_value) FROM v_portfolio_value WHERE status = 'Active'), 1) AS pct_of_aum
FROM v_portfolio_value
WHERE status = 'Active'
GROUP BY size_band
ORDER BY size_band;

-- G5. Mix by account type and by strategy.
-- Looking for: whether the book looks like a real wealth practice
-- (mostly individual and joint accounts, some IRAs and trusts).
SELECT 'account_type' AS dimension, p.account_type AS value,
       COUNT(*) AS portfolios, ROUND(SUM(v.total_value) / 1e6, 1) AS aum_musd
FROM portfolio p JOIN v_portfolio_value v ON v.portfolio_id = p.portfolio_id
WHERE p.status = 'Active'
GROUP BY p.account_type
UNION ALL
SELECT 'strategy', p.strategy, COUNT(*), ROUND(SUM(v.total_value) / 1e6, 1)
FROM portfolio p JOIN v_portfolio_value v ON v.portfolio_id = p.portfolio_id
WHERE p.status = 'Active'
GROUP BY p.strategy
ORDER BY dimension, aum_musd DESC;


-- ---------------------------------------------------------------------
-- 2. GROWTH AND CLIENTS: is the branch winning business?
-- ---------------------------------------------------------------------

-- G6. New portfolios opened and closed per year.
-- Looking for: organic growth (accounts won) against attrition (accounts lost).
SELECT substr(open_date, 1, 4)                           AS year,
       COUNT(*)                                          AS portfolios_opened,
       SUM(status = 'Closed')                            AS of_which_now_closed
FROM portfolio
GROUP BY year
ORDER BY year;

-- G7. Net new money per year (deposits minus withdrawals).
-- Looking for: whether clients are adding money (a sign of trust) or
-- pulling it out.
SELECT substr(flow_date, 1, 4)                                                  AS year,
       ROUND(SUM(CASE WHEN flow_type = 'Deposit'    THEN amount ELSE 0 END) / 1e6, 1) AS deposits_musd,
       ROUND(SUM(CASE WHEN flow_type = 'Withdrawal' THEN amount ELSE 0 END) / 1e6, 1) AS withdrawals_musd,
       ROUND(SUM(CASE WHEN flow_type = 'Deposit' THEN amount ELSE -amount END) / 1e6, 1) AS net_new_money_musd
FROM cash_flow
GROUP BY year
ORDER BY year;

-- G8. Clients with more than one portfolio.
-- Looking for: relationship depth. Households that hold several accounts
-- are stickier and more valuable.
SELECT accounts_per_client, COUNT(*) AS clients
FROM (SELECT client_id, COUNT(*) AS accounts_per_client
      FROM portfolio_owner GROUP BY client_id)
GROUP BY accounts_per_client
ORDER BY accounts_per_client;


-- ---------------------------------------------------------------------
-- 3. PERFORMANCE: are clients making money?
-- ---------------------------------------------------------------------

-- G9. Portfolio returns, with a simple annualized figure.
-- Return = profit / total deposited (withdrawals don't inflate it).
-- Looking for: whether returns are believable. The annualized figure is a
-- simple (non-compounded) approximation: total return x 365 / days open. It
-- ignores the timing of later deposits, so treat it as a rough guide.
-- (Simple, not compounded, because DB Browser's SQLite may lack exp()/ln().)
WITH r AS (
    SELECT v.portfolio_id,
           v.profit / v.total_deposited                                    AS total_return,
           julianday('2026-10-16') - julianday(p.open_date)             AS days_open
    FROM v_portfolio_value v
    JOIN portfolio p ON p.portfolio_id = v.portfolio_id
    WHERE v.status = 'Active' AND v.total_deposited > 0
      AND julianday('2026-10-16') - julianday(p.open_date) >= 180
)
SELECT COUNT(*)                                                             AS portfolios_6m_plus,
       ROUND(100 * AVG(total_return), 1)                                    AS avg_total_return_pct,
       ROUND(100 * AVG(total_return * 365.0 / days_open), 1)                AS avg_simple_annual_pct,
       ROUND(100 * MIN(total_return), 1)                                    AS worst_total_pct,
       ROUND(100 * MAX(total_return), 1)                                    AS best_total_pct,
       SUM(total_return < 0)                                                AS losing_portfolios
FROM r;

-- G10. Performance by manager, with a simple annualized return.
-- Looking for: the spread between the best and worst managers, and whether
-- the stars are believable next to the market benchmark in G10b.
WITH r AS (
    SELECT p.manager_id,
           v.profit, v.total_deposited, v.total_value,
           julianday('2026-10-16') - julianday(p.open_date) AS days_open
    FROM v_portfolio_value v
    JOIN portfolio p ON p.portfolio_id = v.portfolio_id
    WHERE v.status = 'Active' AND v.total_deposited > 0
)
SELECT m.first_name || ' ' || m.last_name                           AS manager,
       m.desk,
       COUNT(r.manager_id)                                         AS portfolios,
       ROUND(SUM(r.total_value) / 1e6, 1)                          AS aum_musd,
       ROUND(100.0 * SUM(r.profit) / SUM(r.total_deposited), 1)       AS total_return_pct,
       ROUND(100.0 * SUM(r.profit) / SUM(r.total_deposited)
             * 365.0 / AVG(r.days_open), 1)                        AS simple_annual_pct
FROM portfolio_manager m
LEFT JOIN r ON r.manager_id = m.manager_id
GROUP BY m.manager_id
ORDER BY total_return_pct DESC;

-- G10b. Benchmark: how much did the S&P 500 ETF (SPY) and a bond ETF (AGG)
-- move over the period, judged from their first trade in the data?
-- Looking for: a yardstick for G9-G11. A manager far above the market for
-- years is a star (or a red flag); one below a bond fund is underperforming.
SELECT s.ticker,
       MIN(t.trade_date)                                                     AS first_trade,
       (SELECT t2.price FROM trade t2 WHERE t2.security_id = s.security_id
        ORDER BY t2.trade_date LIMIT 1)                                      AS first_price,
       s.current_price,
       ROUND(100.0 * (s.current_price /
             (SELECT t2.price FROM trade t2 WHERE t2.security_id = s.security_id
              ORDER BY t2.trade_date LIMIT 1) - 1), 1)                       AS change_pct,
       ROUND(100.0 * (s.current_price /
             (SELECT t2.price FROM trade t2 WHERE t2.security_id = s.security_id
              ORDER BY t2.trade_date LIMIT 1) - 1)
             * 365.0 / (julianday('2026-10-16') - julianday(MIN(t.trade_date))), 1) AS simple_annual_pct
FROM security s
JOIN trade t ON t.security_id = s.security_id
WHERE s.ticker IN ('SPY', 'AGG')
GROUP BY s.security_id;

-- G11. Performance by strategy.
-- Looking for: Growth beating Income in a rising market, with Income steadier.
SELECT p.strategy,
       COUNT(*)                                               AS portfolios,
       ROUND(100.0 * SUM(v.profit) / SUM(v.total_deposited), 1) AS total_return_pct,
       SUM(v.profit < 0)                                      AS losing_portfolios
FROM v_portfolio_value v
JOIN portfolio p ON p.portfolio_id = v.portfolio_id
WHERE v.status = 'Active' AND v.total_deposited > 0
GROUP BY p.strategy
ORDER BY total_return_pct DESC;

-- G12. Biggest positions across the branch.
-- Looking for: concentration in single stocks (risk) and whether the
-- holdings look like a real wealth manager's (mega-caps, index ETFs, Treasuries).
SELECT s.ticker, s.security_name, s.asset_class,
       COUNT(*)                                            AS portfolios_holding,
       ROUND(SUM(h.shares * s.current_price) / 1e6, 1)     AS value_musd,
       ROUND(100.0 * SUM(h.shares * s.current_price)
             / (SELECT SUM(holdings_value) FROM v_portfolio_value), 1) AS pct_of_holdings
FROM v_holdings h
JOIN security s ON s.security_id = h.security_id
GROUP BY s.security_id
ORDER BY value_musd DESC
LIMIT 10;

-- G13. Asset-class mix of everything held.
-- Looking for: a sensible balance of stocks, ETFs and bonds for the strategies.
SELECT s.asset_class,
       ROUND(SUM(h.shares * s.current_price) / 1e6, 1) AS value_musd,
       ROUND(100.0 * SUM(h.shares * s.current_price)
             / (SELECT SUM(holdings_value) FROM v_portfolio_value), 1) AS pct_of_holdings
FROM v_holdings h
JOIN security s ON s.security_id = h.security_id
GROUP BY s.asset_class
ORDER BY value_musd DESC;


-- ---------------------------------------------------------------------
-- 4. PROFITABILITY: does the branch make money for the firm?
-- ---------------------------------------------------------------------

-- G14. Revenue, effective fee rate and manager compensation.
-- Looking for: the effective fee (real firms charge ~0.5-1.0% of AUM) and the
-- compensation ratio (manager pay / revenue; real firms run ~35-50% before
-- other costs). Profit share here is on profit since inception, so it is an
-- upper bound for one year's pay.
WITH pay AS (
    SELECT m.manager_id,
           m.base_salary,
           m.profit_share_pct * MAX(0, COALESCE(SUM(v.profit), 0)) AS profit_share
    FROM portfolio_manager m
    LEFT JOIN v_portfolio_value v ON v.manager_id = m.manager_id
    GROUP BY m.manager_id
),
rev AS (
    SELECT SUM(total_value * fee_pct) AS fees, SUM(total_value) AS aum
    FROM v_portfolio_value WHERE status = 'Active'
)
SELECT ROUND(rev.aum / 1e6, 1)                                         AS aum_musd,
       ROUND(rev.fees / 1e6, 2)                                        AS annual_fees_musd,
       ROUND(100.0 * rev.fees / rev.aum, 3)                            AS effective_fee_pct,
       ROUND(SUM(pay.base_salary) / 1e6, 2)                            AS base_salaries_musd,
       ROUND(SUM(pay.profit_share) / 1e6, 2)                           AS profit_share_musd,
       ROUND(100.0 * SUM(pay.base_salary + pay.profit_share) / rev.fees, 1) AS comp_ratio_pct,
       ROUND(100.0 * SUM(pay.base_salary) / rev.fees, 1)               AS comp_ratio_salary_only_pct
FROM pay, rev;

-- G15. Revenue and pay per manager.
-- Looking for: which managers earn more for the firm than they cost.
-- fee_revenue is the annual fee on their active book; total_pay uses profit since inception.
WITH book AS (
    SELECT p.manager_id,
           SUM(CASE WHEN v.status = 'Active' THEN v.total_value * v.fee_pct ELSE 0 END) AS fee_revenue,
           SUM(CASE WHEN v.status = 'Active' THEN v.total_value ELSE 0 END)             AS aum,
           SUM(v.profit)                                                                 AS profit
    FROM v_portfolio_value v
    JOIN portfolio p ON p.portfolio_id = v.portfolio_id
    GROUP BY p.manager_id
)
SELECT m.first_name || ' ' || m.last_name                                       AS manager,
       ROUND(COALESCE(b.aum, 0) / 1e6, 1)                                       AS aum_musd,
       ROUND(COALESCE(b.fee_revenue, 0) / 1e3, 0)                               AS fee_revenue_kusd,
       ROUND((m.base_salary + m.profit_share_pct * MAX(0, COALESCE(b.profit, 0))) / 1e3, 0) AS total_pay_kusd,
       ROUND((COALESCE(b.fee_revenue, 0)
              - m.base_salary - m.profit_share_pct * MAX(0, COALESCE(b.profit, 0))) / 1e3, 0) AS contribution_kusd,
       ROUND((COALESCE(b.fee_revenue, 0) - m.base_salary) / 1e3, 0)             AS contribution_salary_only_kusd
FROM portfolio_manager m
LEFT JOIN book b ON b.manager_id = m.manager_id
ORDER BY contribution_kusd DESC;

-- G16. Fee revenue by account-size band.
-- Looking for: where the money comes from. Big accounts pay lower rates but
-- usually bring most of the revenue.
SELECT CASE
           WHEN total_value <  1e6 THEN '1. under $1M'
           WHEN total_value <  5e6 THEN '2. $1M-5M'
           WHEN total_value < 25e6 THEN '3. $5M-25M'
           ELSE                         '4. $25M+'
       END                                                  AS size_band,
       ROUND(AVG(fee_pct) * 100, 3)                         AS avg_fee_pct,
       ROUND(SUM(total_value * fee_pct) / 1e6, 2)           AS fees_musd,
       ROUND(100.0 * SUM(total_value * fee_pct)
             / (SELECT SUM(total_value * fee_pct) FROM v_portfolio_value WHERE status = 'Active'), 1) AS pct_of_fees
FROM v_portfolio_value
WHERE status = 'Active'
GROUP BY size_band
ORDER BY size_band;


-- ---------------------------------------------------------------------
-- 5. TRADING: is the activity realistic?
-- ---------------------------------------------------------------------

-- G17. Trading activity per year.
-- Looking for: trades per portfolio and turnover (value traded / AUM).
-- Active wealth managers typically turn over roughly 20-60% of a portfolio a year.
SELECT substr(trade_date, 1, 4)                             AS year,
       COUNT(*)                                             AS trades,
       SUM(side = 'Buy')                                    AS buys,
       SUM(side = 'Sell')                                   AS sells,
       ROUND(SUM(quantity * price) / 1e6, 1)                AS traded_value_musd,
       COUNT(DISTINCT portfolio_id)                         AS portfolios_trading
FROM trade
GROUP BY year
ORDER BY year;

-- G18. Commission cost relative to trading and to AUM.
-- Looking for: commissions as a share of value traded (institutional rates are
-- a few basis points) and as a drag on client returns.
SELECT ROUND(SUM(t.quantity * t.price * b.commission_rate) / 1e6, 2)               AS commissions_musd,
       ROUND(10000.0 * SUM(t.quantity * t.price * b.commission_rate)
             / SUM(t.quantity * t.price), 2)                                       AS commission_bps_of_traded,
       ROUND(10000.0 * SUM(t.quantity * t.price * b.commission_rate)
             / (SELECT SUM(total_value) FROM v_portfolio_value WHERE status = 'Active'), 2) AS commission_bps_of_aum
FROM trade t
JOIN broker b ON b.broker_id = t.broker_id;


-- ---------------------------------------------------------------------
-- 6. DATA SANITY: anything that would look wrong to a grader?
-- ---------------------------------------------------------------------

-- G19. Portfolios whose net invested is zero or negative (more withdrawn than
-- deposited). Looking for: rows where return_pct in Q1 would be misleading.
SELECT portfolio_id, portfolio_name, status,
       ROUND(net_invested, 2) AS net_invested, ROUND(total_value, 2) AS total_value
FROM v_portfolio_value
WHERE net_invested <= 0
ORDER BY net_invested;

-- G20. Extreme returns. Looking for: outliers worth explaining (or fixing)
-- before the demo - a gain above 150% or a loss worse than 20% of deposits.
SELECT v.portfolio_id, v.portfolio_name, p.open_date,
       m.first_name || ' ' || m.last_name           AS manager,
       ROUND(100.0 * v.profit / v.total_deposited, 1)  AS total_return_pct
FROM v_portfolio_value v
JOIN portfolio p         ON p.portfolio_id = v.portfolio_id
JOIN portfolio_manager m ON m.manager_id   = p.manager_id
WHERE v.status = 'Active' AND v.total_deposited > 0
  AND (v.profit / v.total_deposited > 1.5 OR v.profit / v.total_deposited < -0.20)
ORDER BY total_return_pct DESC;

-- G21. Securities with the biggest price change over the period.
-- Looking for: whether simulated price moves are believable
-- (first trade price vs today's price).
WITH first_px AS (
    SELECT security_id, MIN(trade_date) AS first_date
    FROM trade GROUP BY security_id
)
SELECT s.ticker, s.asset_class, f.first_date,
       ROUND(AVG(t.price), 2)                                   AS first_trade_price,
       s.current_price,
       ROUND(100.0 * (s.current_price / AVG(t.price) - 1), 1)   AS change_pct
FROM first_px f
JOIN trade t    ON t.security_id = f.security_id AND t.trade_date = f.first_date
JOIN security s ON s.security_id = f.security_id
GROUP BY s.security_id
ORDER BY change_pct DESC
LIMIT 10;

-- G22. Data-integrity checks on the simulated data (every count should be 0).
-- Looking for: rows that break a business rule the schema can't enforce on its
-- own - overselling, negative cash, ownership not adding to 100%, trades before
-- a portfolio opened, weekend trades, or closed portfolios still holding shares.
SELECT 'sold more shares than held'          AS check_name, COUNT(*) AS problems
FROM (SELECT 1 FROM trade GROUP BY portfolio_id, security_id
      HAVING SUM(CASE WHEN side = 'Buy' THEN quantity ELSE -quantity END) < 0)
UNION ALL
SELECT 'negative cash balance', COUNT(*) FROM v_portfolio_value WHERE cash < -0.01
UNION ALL
SELECT 'ownership not 100%', COUNT(*)
FROM (SELECT 1 FROM portfolio_owner GROUP BY portfolio_id
      HAVING ABS(SUM(ownership_pct) - 100) > 0.001)
UNION ALL
SELECT 'trade before portfolio opened', COUNT(*)
FROM trade t JOIN portfolio p ON p.portfolio_id = t.portfolio_id
WHERE t.trade_date < p.open_date
UNION ALL
SELECT 'trade on a weekend', COUNT(*) FROM trade WHERE strftime('%w', trade_date) IN ('0', '6')
UNION ALL
SELECT 'deposit before client onboarded', COUNT(*)
FROM cash_flow f JOIN client c ON c.client_id = f.client_id
WHERE f.flow_date < c.onboard_date
UNION ALL
SELECT 'closed portfolio still holding', COUNT(*)
FROM v_portfolio_value WHERE status = 'Closed' AND holdings_value <> 0;

-- G23. Story rows: confirm the rows the demo relies on are present.
-- Looking for: trade 1, flow 1 and portfolio 101 matching the data dictionary,
-- the new hire with no book, and the inactive broker with no trades.
SELECT 'trade 1'                   AS item, confirmation_no || ', ' || side || ' ' || quantity || ' @ ' || price AS detail
FROM trade WHERE trade_id = 1
UNION ALL
SELECT 'flow 1', flow_type || ' ' || amount || ' on ' || flow_date FROM cash_flow WHERE flow_id = 1
UNION ALL
SELECT 'portfolio 101', portfolio_name || ' (' || account_type || ', fee ' || fee_pct || ')' FROM portfolio WHERE portfolio_id = 101
UNION ALL
SELECT 'portfolios of manager 6', COUNT(*) FROM portfolio WHERE manager_id = 6
UNION ALL
SELECT 'trades by broker 6', COUNT(*) FROM trade WHERE broker_id = 6;
