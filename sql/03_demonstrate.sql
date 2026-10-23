PRAGMA foreign_keys = ON;   -- SQLite enforces FKs only when this is on


-- ---------------------------------------------------------------------
-- PART A: BUILD CHECKS
-- ---------------------------------------------------------------------

-- A1. Size check: number of tables and columns (expect 8 tables, 55 columns)
SELECT COUNT(DISTINCT m.name) AS tables,
       COUNT(*)               AS columns
FROM sqlite_master m
JOIN pragma_table_info(m.name) p
WHERE m.type = 'table'
  AND m.name NOT LIKE 'sqlite_%';

-- A2. Rows per table, smallest first (expect broker = 6, every table 3+)
SELECT 'client'            AS table_name, COUNT(*) AS row_count FROM client
UNION ALL SELECT 'portfolio_manager', COUNT(*) FROM portfolio_manager
UNION ALL SELECT 'security',          COUNT(*) FROM security
UNION ALL SELECT 'broker',            COUNT(*) FROM broker
UNION ALL SELECT 'portfolio',         COUNT(*) FROM portfolio
UNION ALL SELECT 'trade',             COUNT(*) FROM trade
UNION ALL SELECT 'portfolio_owner',   COUNT(*) FROM portfolio_owner
UNION ALL SELECT 'cash_flow',         COUNT(*) FROM cash_flow
ORDER BY row_count;

-- A3. Foreign keys are switched on (expect 1)
PRAGMA foreign_keys;

-- A4. Orphan check (expect no rows)
PRAGMA foreign_key_check;


-- ---------------------------------------------------------------------
-- PART B: QUERIES THAT ANSWER THE BUSINESS NEED
-- Two views compute holdings and portfolio value once, so the three
-- business questions can reuse them instead of repeating the math.
-- ---------------------------------------------------------------------

-- Holdings: net shares per portfolio and security (buys minus sells).
-- Positions that were sold completely drop out.
DROP VIEW IF EXISTS v_portfolio_value;
DROP VIEW IF EXISTS v_holdings;
CREATE VIEW v_holdings AS
SELECT t.portfolio_id,
       t.security_id,
       SUM(CASE WHEN t.side = 'Buy' THEN t.quantity ELSE -t.quantity END) AS shares
FROM trade t
GROUP BY t.portfolio_id, t.security_id
HAVING shares <> 0;

-- Portfolio value, built from stored facts only:
--   total_deposited = all deposits ever made (the base for return %)
--   net_invested   = deposits - withdrawals
--   commission     = quantity x price x broker.commission_rate
--   cash           = net_invested - buys + sells - commissions
--   holdings_value = SUM(shares x current_price)
--   total_value    = holdings_value + cash
--   profit         = total_value - net_invested
CREATE VIEW v_portfolio_value AS
WITH flows AS (
    SELECT portfolio_id,
           SUM(CASE WHEN flow_type = 'Deposit' THEN amount ELSE 0 END)       AS total_deposited,
           SUM(CASE WHEN flow_type = 'Deposit' THEN amount ELSE -amount END) AS net_invested
    FROM cash_flow
    GROUP BY portfolio_id
),
trade_cash AS (
    SELECT t.portfolio_id,
           SUM(CASE WHEN t.side = 'Sell' THEN t.quantity * t.price ELSE -t.quantity * t.price END
               - t.quantity * t.price * b.commission_rate) AS trade_cash
    FROM trade t
    JOIN broker b ON b.broker_id = t.broker_id
    GROUP BY t.portfolio_id
),
market AS (
    SELECT h.portfolio_id,
           SUM(h.shares * s.current_price) AS holdings_value
    FROM v_holdings h
    JOIN security s ON s.security_id = h.security_id
    GROUP BY h.portfolio_id
)
SELECT p.portfolio_id,
       p.portfolio_name,
       p.manager_id,
       p.status,
       p.fee_pct,
       COALESCE(m.holdings_value, 0)                                       AS holdings_value,
       COALESCE(f.net_invested, 0) + COALESCE(tc.trade_cash, 0)            AS cash,
       COALESCE(m.holdings_value, 0) + COALESCE(f.net_invested, 0)
                                     + COALESCE(tc.trade_cash, 0)          AS total_value,
       COALESCE(f.total_deposited, 0)                                      AS total_deposited,
       COALESCE(f.net_invested, 0)                                         AS net_invested,
       COALESCE(m.holdings_value, 0) + COALESCE(tc.trade_cash, 0)          AS profit
FROM portfolio p
LEFT JOIN flows      f  ON f.portfolio_id  = p.portfolio_id
LEFT JOIN trade_cash tc ON tc.portfolio_id = p.portfolio_id
LEFT JOIN market     m  ON m.portfolio_id  = p.portfolio_id;


-- Q1. As of today, what does each portfolio hold, what is it worth at current
--     prices (including uninvested cash), and how much profit has it made since
--     it opened compared with the money its clients put in?
--     WHERE status = 'Active' leaves out the closed portfolios.
--     return_pct = profit / total deposited, so withdrawals don't inflate it.
--     Portfolios 698-700 show cash only (no trades yet).
SELECT v.portfolio_id,
       v.portfolio_name,
       COUNT(h.security_id)                          AS positions,
       ROUND(v.holdings_value, 2)                    AS holdings_value,
       ROUND(v.cash, 2)                              AS cash,
       ROUND(v.total_value, 2)                       AS total_value,
       ROUND(v.net_invested, 2)                      AS net_invested,
       ROUND(v.profit, 2)                            AS profit,
       ROUND(100.0 * v.profit / v.total_deposited, 1) AS return_pct
FROM v_portfolio_value v
LEFT JOIN v_holdings h ON h.portfolio_id = v.portfolio_id
WHERE v.status = 'Active'
GROUP BY v.portfolio_id
ORDER BY v.profit DESC;

-- Q1 (detail). What exactly does portfolio 101 (Elena and Daniel Ruiz) hold?
--     5-way JOIN: holdings -> security, portfolio, portfolio_owner, client.
SELECT p.portfolio_name,
       GROUP_CONCAT(DISTINCT c.first_name || ' ' || c.last_name) AS owners,
       s.ticker,
       s.security_name,
       s.asset_class,
       h.shares,
       s.current_price,
       ROUND(h.shares * s.current_price, 2)                      AS market_value
FROM v_holdings h
JOIN security        s  ON s.security_id   = h.security_id
JOIN portfolio       p  ON p.portfolio_id  = h.portfolio_id
JOIN portfolio_owner po ON po.portfolio_id = p.portfolio_id
JOIN client          c  ON c.client_id     = po.client_id
WHERE p.portfolio_id = 101
GROUP BY s.security_id
ORDER BY market_value DESC;


-- Q2. Using profit since inception at today's prices, how much is each
--     portfolio manager owed (base salary plus their profit share), and which
--     managers have generated the most profit for clients?
--     LEFT JOIN keeps Gabriela Santos (new hire, no portfolios) at base salary;
--     MAX(0, ...) means managers who lost client money earn no profit share.
SELECT m.manager_id,
       m.first_name || ' ' || m.last_name                                   AS manager,
       m.desk,
       COUNT(v.portfolio_id)                                                AS portfolios,
       ROUND(COALESCE(SUM(v.profit), 0), 2)                                 AS client_profit,
       m.base_salary,
       ROUND(m.profit_share_pct * MAX(0, COALESCE(SUM(v.profit), 0)), 2)    AS profit_share,
       ROUND(m.base_salary
             + m.profit_share_pct * MAX(0, COALESCE(SUM(v.profit), 0)), 2)  AS total_pay
FROM portfolio_manager m
LEFT JOIN v_portfolio_value v ON v.manager_id = m.manager_id
GROUP BY m.manager_id
ORDER BY client_profit DESC;


-- Q3. At today's portfolio values, how much does the firm expect to earn in
--     annual fees compared with what it owes its managers?
--     Fees = total_value x fee_pct on active portfolios.
WITH manager_pay AS (
    SELECT m.manager_id,
           m.base_salary + m.profit_share_pct * MAX(0, COALESCE(SUM(v.profit), 0)) AS pay
    FROM portfolio_manager m
    LEFT JOIN v_portfolio_value v ON v.manager_id = m.manager_id
    GROUP BY m.manager_id
)
SELECT ROUND((SELECT SUM(total_value) FROM v_portfolio_value WHERE status = 'Active'), 2)
                                                                         AS assets_under_mgmt,
       ROUND((SELECT SUM(total_value * fee_pct) FROM v_portfolio_value WHERE status = 'Active'), 2)
                                                                         AS est_annual_fees,
       ROUND((SELECT SUM(pay) FROM manager_pay), 2)                      AS manager_pay,
       ROUND((SELECT SUM(total_value * fee_pct) FROM v_portfolio_value WHERE status = 'Active')
             - (SELECT SUM(pay) FROM manager_pay), 2)                    AS fees_minus_pay;

-- Q3 (brokers). How much has each broker charged in commissions?
--     LEFT JOIN keeps Old Quay Securities (inactive, no trades) at $0.
SELECT b.broker_name,
       b.is_active,
       b.commission_rate,
       COUNT(t.trade_id)                                                AS trades,
       ROUND(COALESCE(SUM(t.quantity * t.price), 0), 2)                 AS traded_value,
       ROUND(COALESCE(SUM(t.quantity * t.price * b.commission_rate), 0), 2) AS commissions
FROM broker b
LEFT JOIN trade t ON t.broker_id = b.broker_id
GROUP BY b.broker_id
ORDER BY commissions DESC;


-- ---------------------------------------------------------------------
-- PART C: PROVE THE RULES WORK (each statement below SHOULD FAIL)
-- ---------------------------------------------------------------------

-- C1. Rule 1, NOT NULL: a portfolio must have a manager
-- Expect: NOT NULL constraint failed: portfolio.manager_id
--INSERT INTO portfolio (portfolio_id, manager_id, portfolio_name, account_type, strategy, fee_pct, open_date) VALUES (999, NULL, 'Ghost Portfolio', 'Individual', 'Growth', 0.01, '2026-10-20');

-- C2. Rule 3b, FOREIGN KEY: a trade must be for a security that exists
-- Expect: FOREIGN KEY constraint failed
--INSERT INTO trade (trade_id, confirmation_no, portfolio_id, security_id, broker_id, trade_date, side, quantity, price, settlement_date) VALUES (99999, 'NB-99999', 101, 999, 1, '2026-10-20', 'Buy', 10, 100.00, '2026-10-21');

-- C3. Rule 5b, composite FOREIGN KEY: only an owner can deposit into a portfolio
--     (client 7 is not an owner of portfolio 101)
-- Expect: FOREIGN KEY constraint failed
--INSERT INTO cash_flow (flow_id, portfolio_id, client_id, flow_date, flow_type, amount) VALUES (99999, 101, 7, '2026-10-20', 'Deposit', 50000.00);

-- C4. Rule 7, CHECK: side must be Buy or Sell
-- Expect: CHECK constraint failed: side IN ('Buy','Sell')
--INSERT INTO trade (trade_id, confirmation_no, portfolio_id, security_id, broker_id, trade_date, side, quantity, price, settlement_date) VALUES (99999, 'NB-99999', 101, 3, 1, '2026-10-20', 'Hold', 10, 100.00, '2026-10-21');

-- C5. Rule 8, CHECK: ownership must be greater than 0 and no more than 100
-- Expect: CHECK constraint failed: ownership_pct > 0 AND ownership_pct <= 100
--INSERT INTO portfolio_owner (portfolio_id, client_id, ownership_pct, added_date) VALUES (101, 7, 150, '2026-10-20');

-- C6. Rule 9, CHECK: settlement cannot be earlier than the trade date
-- Expect: CHECK constraint failed: settlement_date >= trade_date
--INSERT INTO trade (trade_id, confirmation_no, portfolio_id, security_id, broker_id, trade_date, side, quantity, price, settlement_date) VALUES (99999, 'NB-99999', 101, 3, 1, '2026-10-20', 'Buy', 10, 100.00, '2026-10-16');

-- C7. Rule 6, UNIQUE: the same broker confirmation cannot be entered twice
-- Expect: UNIQUE constraint failed: trade.confirmation_no
--INSERT INTO trade (trade_id, confirmation_no, portfolio_id, security_id, broker_id, trade_date, side, quantity, price, settlement_date) VALUES (99999, 'GS-10482', 101, 3, 2, '2026-09-15', 'Buy', 200, 238.86, '2026-09-16');


-- ---------------------------------------------------------------------
-- PART D: A FILTERED SAMPLE FROM EACH TABLE
-- One WHERE-filtered query per table, showing how each table is used day
-- to day. Expected row counts are for the sample data in 02_load.sql.
-- ---------------------------------------------------------------------

-- D1. client: aggressive-risk clients onboarded since 2024
--     (candidates for a growth-strategy review). Expect 42 rows.
SELECT client_id, first_name, last_name, risk_profile, onboard_date
FROM client
WHERE risk_profile = 'Aggressive'
  AND onboard_date >= '2024-01-01'
ORDER BY onboard_date;

-- D2. portfolio_manager: senior Equity-desk managers hired before 2020,
--     with their pay terms. Expect 4 rows.
SELECT manager_id, first_name || ' ' || last_name AS manager, hire_date,
       base_salary, profit_share_pct
FROM portfolio_manager
WHERE desk = 'Equity'
  AND hire_date < '2020-01-01'
ORDER BY hire_date;

-- D3. security: the approved bond list, cheapest first. Expect 10 rows.
SELECT security_id, ticker, security_name, current_price, price_date
FROM security
WHERE asset_class = 'Bond'
ORDER BY current_price;

-- D4. broker: active brokers charging less than 0.06% commission
--     (the low-cost routing list). Expect 3 rows.
SELECT broker_id, broker_name, commission_rate
FROM broker
WHERE is_active = 1
  AND commission_rate < 0.0006
ORDER BY commission_rate;

-- D5. portfolio: Joint accounts with a Growth strategy opened since 2024.
--     Expect 15 rows.
SELECT portfolio_id, portfolio_name, manager_id, fee_pct, open_date, status
FROM portfolio
WHERE account_type = 'Joint'
  AND strategy = 'Growth'
  AND open_date >= '2024-01-01'
ORDER BY open_date;

-- D6. trade: large sells (over $1M) placed in 2026 - the trades a
--     compliance officer would review first. Expect 28 rows.
SELECT trade_id, confirmation_no, portfolio_id, security_id, trade_date,
       quantity, price, ROUND(quantity * price, 2) AS trade_value
FROM trade
WHERE side = 'Sell'
  AND trade_date >= '2026-01-01'
  AND quantity * price > 1000000
ORDER BY trade_value DESC;

-- D7. portfolio_owner: minority owners (less than 50% of a portfolio),
--     e.g. children named on a family trust. Expect 122 rows.
SELECT portfolio_id, client_id, ownership_pct, added_date
FROM portfolio_owner
WHERE ownership_pct < 50
ORDER BY portfolio_id, ownership_pct;

-- D8. cash_flow: withdrawals of $1M or more in 2026 (large outflows the
--     relationship manager should follow up on). Expect 8 rows.
SELECT flow_id, portfolio_id, client_id, flow_date, amount
FROM cash_flow
WHERE flow_type = 'Withdrawal'
  AND flow_date >= '2026-01-01'
  AND amount >= 1000000
ORDER BY amount DESC;
