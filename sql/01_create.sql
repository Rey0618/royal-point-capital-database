PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS cash_flow;
DROP TABLE IF EXISTS portfolio_owner;
DROP TABLE IF EXISTS trade;
DROP TABLE IF EXISTS portfolio;
DROP TABLE IF EXISTS broker;
DROP TABLE IF EXISTS security;
DROP TABLE IF EXISTS portfolio_manager;
DROP TABLE IF EXISTS client;

CREATE TABLE client (
    client_id      INTEGER PRIMARY KEY,
    first_name     TEXT    NOT NULL,
    last_name      TEXT    NOT NULL,
    email          TEXT    NOT NULL UNIQUE,
    date_of_birth  TEXT    NOT NULL,                       -- YYYY-MM-DD
    risk_profile   TEXT    NOT NULL
                   CHECK (risk_profile IN ('Conservative','Moderate','Aggressive')),
    onboard_date   TEXT    NOT NULL DEFAULT (date('now'))  -- YYYY-MM-DD
);

CREATE TABLE portfolio_manager (
    manager_id        INTEGER PRIMARY KEY,
    first_name        TEXT    NOT NULL,
    last_name         TEXT    NOT NULL,
    email             TEXT    NOT NULL UNIQUE,
    desk              TEXT    NOT NULL
                      CHECK (desk IN ('Equity','Fixed Income','Multi-Asset')),
    hire_date         TEXT    NOT NULL,                    -- YYYY-MM-DD
    base_salary       REAL    NOT NULL CHECK (base_salary > 0),
    profit_share_pct  REAL    NOT NULL CHECK (profit_share_pct BETWEEN 0 AND 1)
);

CREATE TABLE security (
    security_id    INTEGER PRIMARY KEY,
    ticker         TEXT    NOT NULL UNIQUE,
    security_name  TEXT    NOT NULL,
    asset_class    TEXT    NOT NULL CHECK (asset_class IN ('Equity','ETF','Bond')),
    sector         TEXT,                                   -- optional: bonds and broad ETFs have none
    current_price  REAL    NOT NULL CHECK (current_price > 0),
    price_date     TEXT    NOT NULL                        -- YYYY-MM-DD
);

CREATE TABLE broker (
    broker_id        INTEGER PRIMARY KEY,
    broker_name      TEXT    NOT NULL UNIQUE,
    contact_email    TEXT,
    commission_rate  REAL    NOT NULL CHECK (commission_rate BETWEEN 0 AND 1),
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE portfolio (
    portfolio_id    INTEGER PRIMARY KEY,
    manager_id      INTEGER NOT NULL,
    portfolio_name  TEXT    NOT NULL,
    account_type    TEXT    NOT NULL
                    CHECK (account_type IN ('Individual','Joint','IRA','Trust')),
    strategy        TEXT    NOT NULL
                    CHECK (strategy IN ('Growth','Income','Balanced')),
    fee_pct         REAL    NOT NULL CHECK (fee_pct BETWEEN 0 AND 1),
    open_date       TEXT    NOT NULL,                      -- YYYY-MM-DD
    status          TEXT    NOT NULL DEFAULT 'Active'
                    CHECK (status IN ('Active','Closed')),
    FOREIGN KEY (manager_id) REFERENCES portfolio_manager(manager_id)
);

CREATE TABLE trade (
    trade_id         INTEGER PRIMARY KEY,
    confirmation_no  TEXT    NOT NULL UNIQUE,
    portfolio_id     INTEGER NOT NULL,
    security_id      INTEGER NOT NULL,
    broker_id        INTEGER NOT NULL,
    trade_date       TEXT    NOT NULL,                     -- YYYY-MM-DD
    side             TEXT    NOT NULL CHECK (side IN ('Buy','Sell')),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    price            REAL    NOT NULL CHECK (price > 0),
    settlement_date  TEXT    NOT NULL,                     -- YYYY-MM-DD
    CHECK (settlement_date >= trade_date),
    FOREIGN KEY (portfolio_id) REFERENCES portfolio(portfolio_id),
    FOREIGN KEY (security_id)  REFERENCES security(security_id),
    FOREIGN KEY (broker_id)    REFERENCES broker(broker_id)
);

-- ---------------------------------------------------------------------
-- STEP 3: the associative table, and the table that points at it
-- ---------------------------------------------------------------------

-- Portfolio_Owner (4 columns) - resolves the client-portfolio many-to-many
-- Rule 2: a client may own many portfolios and a portfolio may have many owners.
--         (Every portfolio having at least one owner is enforced by the application.)
-- Rule 8: ownership_pct is greater than 0 and no more than 100. It lives HERE
--         because it depends on BOTH the client and the portfolio.
CREATE TABLE portfolio_owner (
    portfolio_id   INTEGER NOT NULL,
    client_id      INTEGER NOT NULL,
    ownership_pct  REAL    NOT NULL CHECK (ownership_pct > 0 AND ownership_pct <= 100),
    added_date     TEXT    NOT NULL DEFAULT (date('now')),  -- YYYY-MM-DD
    PRIMARY KEY (portfolio_id, client_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolio(portfolio_id),
    FOREIGN KEY (client_id)    REFERENCES client(client_id)
);

-- Cash_Flow (6 columns)
-- Rules 5a/5b: each deposit or withdrawal is made by exactly one client into
--              exactly one portfolio, and that client must OWN the portfolio.
--              One composite FK to portfolio_owner enforces both at once.
-- Rule 10: flow_type is Deposit or Withdrawal, and amount is greater than zero.
CREATE TABLE cash_flow (
    flow_id       INTEGER PRIMARY KEY,
    portfolio_id  INTEGER NOT NULL,
    client_id     INTEGER NOT NULL,
    flow_date     TEXT    NOT NULL,                        -- YYYY-MM-DD
    flow_type     TEXT    NOT NULL CHECK (flow_type IN ('Deposit','Withdrawal')),
    amount        REAL    NOT NULL CHECK (amount > 0),
    FOREIGN KEY (portfolio_id, client_id)
        REFERENCES portfolio_owner(portfolio_id, client_id)
);
