"""
Royal Point Capital: sample-data generator for the A1 SQLite build.

Writes sql/02_load.sql (the INSERT statements) for one regional office of the
firm: 15 portfolio managers and 600 portfolios, with a client book built up
since 2015. The tables themselves are created by sql/01_create.sql.

The data is simulated, not hand-typed, so every row obeys the business rules:
- no sell is larger than the shares held, and cash never goes negative
- every cash flow is made by an owner of that portfolio
- each portfolio's ownership percentages add up to 100
- settlement is T+3 before 2017-09-05, T+2 until 2024-05-28 and T+1 after,
  skipping weekends
- prices move together through a shared market factor (stocks and ETFs) and
  an interest-rate factor (bonds), with lower volatility for defensive sectors

Run (from anywhere; standard library only, Python 3.8+):
    python3 scripts/generate_royal_point_data.py
The seed is fixed, so every run produces the same file.
"""
import math
import os
import random
from datetime import date, timedelta

SEED = 301
LOAD_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sql', '02_load.sql')
PRICE_DATE = date(2026, 10, 16)       # date of security.current_price
LAST_TRADE = date(2026, 10, 15)       # no events after this date
FIRST_OPEN = date(2015, 1, 2)        # the branch's client book starts here
T2_START = date(2017, 9, 5)           # US settlement moved from T+3 to T+2
T1_START = date(2024, 5, 28)          # ...and from T+2 to T+1
N_PORTFOLIOS = 600

rng = random.Random(SEED)

# --------------------------------------------------------------------------- reference data
FIRST = ['James', 'Maria', 'Wei', 'Aisha', 'Carlos', 'Priya', 'Thomas', 'Sofia', 'Kenji', 'Fatima', 'Michael',
         'Ana', 'David', 'Mei', 'Omar', 'Laura', 'Daniel', 'Grace', 'Rahul', 'Isabel', 'Samuel', 'Hannah', 'Luis',
         'Chloe', 'Arjun', 'Emma', 'Jorge', 'Olivia', 'Tariq', 'Lucia', 'Benjamin', 'Yuki', 'Andre', 'Nadia',
         'Patrick', 'Elena', 'Victor', 'Amara', 'Henry', 'Sara', 'Diego', 'Claire', 'Ibrahim', 'Rosa', 'Nathan',
         'Leila', 'George', 'Ingrid', 'Mateo', 'Ruth', 'Kwame', 'Julia', 'Hugo', 'Zara', 'Peter', 'Camila',
         'Ethan', 'Noor', 'Adrian', 'Beatriz', 'Felix', 'Hana', 'Marcus', 'Alicia', 'Raj', 'Monica', 'Oscar',
         'Daniela', 'Leo', 'Sienna', 'Malik', 'Teresa', 'Simon', 'Ayumi', 'Rafael', 'Eva', 'Charles', 'Lina',
         'Gabriel', 'Nora', 'Kofi', 'Valeria', 'William', 'Ines', 'Martin', 'Rania', 'Paul', 'Alma', 'Ricardo',
         'Helen', 'Sean', 'Mariam', 'Jonah', 'Paula', 'Viktor', 'Jasmine', 'Edward', 'Selin', 'Tomas', 'Ava']
LAST = ['Smith', 'Garcia', 'Chen', 'Patel', 'Johnson', 'Rodriguez', 'Kim', 'Nguyen', 'Williams', 'Martinez',
        'Brown', 'Lopez', 'Singh', 'Davis', 'Hernandez', 'Wang', 'Miller', 'Gonzalez', 'Khan', 'Wilson',
        'Anderson', 'Perez', 'Taylor', 'Sanchez', 'Thomas', 'Ramirez', 'Moore', 'Torres', 'Jackson', 'Flores',
        'White', 'Rivera', 'Harris', 'Gomez', 'Clark', 'Diaz', 'Lewis', 'Cruz', 'Robinson', 'Morales', 'Walker',
        'Ortiz', 'Young', 'Gutierrez', 'Allen', 'Chavez', 'King', 'Ramos', 'Wright', 'Ruiz', 'Scott', 'Alvarez',
        'Green', 'Mendoza', 'Baker', 'Castillo', 'Adams', 'Vargas', 'Nelson', 'Romero', 'Hill', 'Herrera',
        'Campbell', 'Medina', 'Mitchell', 'Aguilar', 'Roberts', 'Silva', 'Carter', 'Reyes', 'Phillips', 'Moreno',
        'Evans', 'Jimenez', 'Turner', 'Molina', 'Parker', 'Delgado', 'Collins', 'Castro', 'Edwards', 'Ortega',
        'Stewart', 'Rojas', 'Morris', 'Navarro', 'Murphy', 'Fischer', 'Cook', 'Nakamura', 'Rogers', 'Okafor',
        'Morgan', 'Haddad', 'Cooper', 'Kowalski', 'Peterson', 'Rossi', 'Bailey', 'Novak', 'Reed', 'Sato',
        'Kelly', 'Mensah', 'Howard', 'Dubois', 'Ward', 'Larsen', 'Cox', 'Ibrahim', 'Richardson', 'Moreau',
        'Watson', 'Ferreira', 'Brooks', 'Yilmaz', 'Wood', 'Schmidt', 'James', 'Bianchi', 'Bennett', 'Andersson',
        'Gray', 'Costa', 'Hughes', 'Tanaka', 'Price', 'Petrov', 'Sanders', 'Murray', 'Foster', 'Ali', 'Long',
        'Banerjee', 'Ross', 'Lindqvist', 'Powell', 'Mehta', 'Jenkins', 'Ahmed', 'Perry', 'Suzuki', 'Butler']

# (name, desk, hire_date, base_salary, profit_share_pct, skill)
# skill tilts security selection toward (+) or away from (-) the eventual winners.
MANAGERS = [
    ('Marcus', 'Lee', 'Equity', '2019-09-03', 185000, 0.004, 4.0),
    ('Rebecca', 'Holt', 'Equity', '2015-04-13', 240000, 0.004, 2.0),
    ('Anil', 'Kapoor', 'Equity', '2017-01-09', 210000, 0.0045, 1.0),
    ('Sarah', 'Donnelly', 'Equity', '2021-06-14', 165000, 0.003, -3.0),
    ('Tobias', 'Wren', 'Equity', '2012-10-01', 260000, 0.005, 0.5),
    ('Gabriela', 'Santos', 'Equity', '2026-08-17', 140000, 0.0025, 0.0),   # new hire, no book yet
    ('Howard', 'Pierce', 'Fixed Income', '2010-03-22', 230000, 0.004, 1.0),
    ('Lin', 'Zhao', 'Fixed Income', '2016-08-29', 195000, 0.004, 2.5),
    ('Martin', 'Achebe', 'Fixed Income', '2020-02-10', 170000, 0.003, -1.0),
    ('Claire', 'Bouchard', 'Fixed Income', '2018-11-05', 185000, 0.004, 0.0),
    ('Daniel', 'Okonkwo', 'Multi-Asset', '2014-05-19', 225000, 0.0045, 3.0),
    ('Isabel', 'Navarro', 'Multi-Asset', '2019-01-28', 180000, 0.004, -2.0),
    ('Kevin', 'Brandt', 'Multi-Asset', '2013-07-15', 235000, 0.004, 1.5),
    ('Yara', 'Haddad', 'Multi-Asset', '2022-09-12', 160000, 0.003, -8.0),
    ('Owen', 'Fitzgerald', 'Multi-Asset', '2011-12-05', 250000, 0.005, 0.0),
]
NEW_HIRE = 6  # manager_id of Gabriela Santos

# (name, prefix, email, commission_rate, is_active, routing weight)
BROKERS = [
    ('Northbridge Capital Markets', 'NB', 'execution@northbridgecm.example', 0.0004, 1, 0.25),
    ('Granite Street Securities', 'GS', 'desk@granitestreet.example', 0.0005, 1, 0.30),
    ('Harbor & Vine Securities', 'HV', 'trading@harborvine.example', 0.0008, 1, 0.20),
    ('Meridian Execution Partners', 'ME', 'desk@meridianexec.example', 0.0003, 1, 0.15),
    ('Lakeshore Brokerage', 'LB', None, 0.0010, 1, 0.10),
    ('Old Quay Securities', 'OQ', 'info@oldquay.example', 0.0012, 0, 0.0),
]

# (ticker, name, asset_class, sector, current_price)
SECURITIES = [
    ('MSFT', 'Microsoft Corp.', 'Equity', 'Technology', 428.50),
    ('NVDA', 'NVIDIA Corp.', 'Equity', 'Technology', 138.20),
    ('AAPL', 'Apple Inc.', 'Equity', 'Technology', 231.10),
    ('AVGO', 'Broadcom Inc.', 'Equity', 'Technology', 172.40),
    ('ORCL', 'Oracle Corp.', 'Equity', 'Technology', 168.90),
    ('CRM', 'Salesforce Inc.', 'Equity', 'Technology', 289.30),
    ('ADBE', 'Adobe Inc.', 'Equity', 'Technology', 512.60),
    ('AMD', 'Advanced Micro Devices Inc.', 'Equity', 'Technology', 156.70),
    ('INTC', 'Intel Corp.', 'Equity', 'Technology', 23.10),
    ('CSCO', 'Cisco Systems Inc.', 'Equity', 'Technology', 55.40),
    ('IBM', 'International Business Machines Corp.', 'Equity', 'Technology', 221.80),
    ('QCOM', 'Qualcomm Inc.', 'Equity', 'Technology', 168.20),
    ('TXN', 'Texas Instruments Inc.', 'Equity', 'Technology', 198.40),
    ('NOW', 'ServiceNow Inc.', 'Equity', 'Technology', 905.10),
    ('INTU', 'Intuit Inc.', 'Equity', 'Technology', 640.20),
    ('AMAT', 'Applied Materials Inc.', 'Equity', 'Technology', 186.30),
    ('MU', 'Micron Technology Inc.', 'Equity', 'Technology', 98.70),
    ('GOOGL', 'Alphabet Inc. Class A', 'Equity', 'Communication Services', 165.80),
    ('META', 'Meta Platforms Inc.', 'Equity', 'Communication Services', 576.40),
    ('NFLX', 'Netflix Inc.', 'Equity', 'Communication Services', 712.30),
    ('DIS', 'Walt Disney Co.', 'Equity', 'Communication Services', 96.20),
    ('VZ', 'Verizon Communications Inc.', 'Equity', 'Communication Services', 43.60),
    ('T', 'AT&T Inc.', 'Equity', 'Communication Services', 22.40),
    ('TMUS', 'T-Mobile US Inc.', 'Equity', 'Communication Services', 221.50),
    ('CMCSA', 'Comcast Corp.', 'Equity', 'Communication Services', 41.80),
    ('AMZN', 'Amazon.com Inc.', 'Equity', 'Consumer Discretionary', 186.40),
    ('TSLA', 'Tesla Inc.', 'Equity', 'Consumer Discretionary', 248.50),
    ('HD', 'Home Depot Inc.', 'Equity', 'Consumer Discretionary', 401.20),
    ('MCD', "McDonald's Corp.", 'Equity', 'Consumer Discretionary', 302.70),
    ('NKE', 'Nike Inc.', 'Equity', 'Consumer Discretionary', 81.40),
    ('SBUX', 'Starbucks Corp.', 'Equity', 'Consumer Discretionary', 97.30),
    ('LOW', "Lowe's Companies Inc.", 'Equity', 'Consumer Discretionary', 263.10),
    ('BKNG', 'Booking Holdings Inc.', 'Equity', 'Consumer Discretionary', 4210.00),
    ('TJX', 'TJX Companies Inc.', 'Equity', 'Consumer Discretionary', 117.80),
    ('CMG', 'Chipotle Mexican Grill Inc.', 'Equity', 'Consumer Discretionary', 57.40),
    ('PG', 'Procter & Gamble Co.', 'Equity', 'Consumer Staples', 171.20),
    ('KO', 'Coca-Cola Co.', 'Equity', 'Consumer Staples', 70.10),
    ('PEP', 'PepsiCo Inc.', 'Equity', 'Consumer Staples', 168.90),
    ('WMT', 'Walmart Inc.', 'Equity', 'Consumer Staples', 80.60),
    ('COST', 'Costco Wholesale Corp.', 'Equity', 'Consumer Staples', 892.40),
    ('CL', 'Colgate-Palmolive Co.', 'Equity', 'Consumer Staples', 93.70),
    ('MDLZ', 'Mondelez International Inc.', 'Equity', 'Consumer Staples', 71.50),
    ('PM', 'Philip Morris International Inc.', 'Equity', 'Consumer Staples', 121.30),
    ('UNH', 'UnitedHealth Group Inc.', 'Equity', 'Health Care', 584.20),
    ('JNJ', 'Johnson & Johnson', 'Equity', 'Health Care', 158.90),
    ('LLY', 'Eli Lilly and Co.', 'Equity', 'Health Care', 893.40),
    ('PFE', 'Pfizer Inc.', 'Equity', 'Health Care', 28.70),
    ('MRK', 'Merck & Co. Inc.', 'Equity', 'Health Care', 110.30),
    ('ABBV', 'AbbVie Inc.', 'Equity', 'Health Care', 192.80),
    ('TMO', 'Thermo Fisher Scientific Inc.', 'Equity', 'Health Care', 601.20),
    ('ABT', 'Abbott Laboratories', 'Equity', 'Health Care', 114.60),
    ('AMGN', 'Amgen Inc.', 'Equity', 'Health Care', 318.40),
    ('ISRG', 'Intuitive Surgical Inc.', 'Equity', 'Health Care', 488.10),
    ('CVS', 'CVS Health Corp.', 'Equity', 'Health Care', 58.90),
    ('JPM', 'JPMorgan Chase & Co.', 'Equity', 'Financials', 221.40),
    ('BAC', 'Bank of America Corp.', 'Equity', 'Financials', 41.20),
    ('WFC', 'Wells Fargo & Co.', 'Equity', 'Financials', 63.80),
    ('GS', 'Goldman Sachs Group Inc.', 'Equity', 'Financials', 512.30),
    ('MS', 'Morgan Stanley', 'Equity', 'Financials', 118.60),
    ('BLK', 'BlackRock Inc.', 'Equity', 'Financials', 960.20),
    ('SCHW', 'Charles Schwab Corp.', 'Equity', 'Financials', 68.40),
    ('V', 'Visa Inc.', 'Equity', 'Financials', 289.50),
    ('MA', 'Mastercard Inc.', 'Equity', 'Financials', 502.10),
    ('AXP', 'American Express Co.', 'Equity', 'Financials', 271.30),
    ('BRK.B', 'Berkshire Hathaway Inc. Class B', 'Equity', 'Financials', 462.70),
    ('C', 'Citigroup Inc.', 'Equity', 'Financials', 63.90),
    ('CAT', 'Caterpillar Inc.', 'Equity', 'Industrials', 385.20),
    ('HON', 'Honeywell International Inc.', 'Equity', 'Industrials', 213.40),
    ('UNP', 'Union Pacific Corp.', 'Equity', 'Industrials', 241.80),
    ('GE', 'GE Aerospace', 'Equity', 'Industrials', 186.70),
    ('BA', 'Boeing Co.', 'Equity', 'Industrials', 152.30),
    ('LMT', 'Lockheed Martin Corp.', 'Equity', 'Industrials', 584.60),
    ('UPS', 'United Parcel Service Inc.', 'Equity', 'Industrials', 131.20),
    ('DE', 'Deere & Co.', 'Equity', 'Industrials', 402.10),
    ('RTX', 'RTX Corp.', 'Equity', 'Industrials', 121.50),
    ('XOM', 'Exxon Mobil Corp.', 'Equity', 'Energy', 118.40),
    ('CVX', 'Chevron Corp.', 'Equity', 'Energy', 152.60),
    ('COP', 'ConocoPhillips', 'Equity', 'Energy', 106.30),
    ('SLB', 'Schlumberger Ltd.', 'Equity', 'Energy', 42.70),
    ('EOG', 'EOG Resources Inc.', 'Equity', 'Energy', 125.80),
    ('NEE', 'NextEra Energy Inc.', 'Equity', 'Utilities', 79.40),
    ('DUK', 'Duke Energy Corp.', 'Equity', 'Utilities', 116.20),
    ('SO', 'Southern Co.', 'Equity', 'Utilities', 89.70),
    ('D', 'Dominion Energy Inc.', 'Equity', 'Utilities', 57.30),
    ('PLD', 'Prologis Inc.', 'Equity', 'Real Estate', 121.60),
    ('AMT', 'American Tower Corp.', 'Equity', 'Real Estate', 228.40),
    ('O', 'Realty Income Corp.', 'Equity', 'Real Estate', 62.10),
    ('SPG', 'Simon Property Group Inc.', 'Equity', 'Real Estate', 166.80),   # approved but never traded
    ('LIN', 'Linde plc', 'Equity', 'Materials', 468.30),
    ('SHW', 'Sherwin-Williams Co.', 'Equity', 'Materials', 372.50),
    ('FCX', 'Freeport-McMoRan Inc.', 'Equity', 'Materials', 47.20),
    ('NEM', 'Newmont Corp.', 'Equity', 'Materials', 53.10),
    ('SPY', 'SPDR S&P 500 ETF Trust', 'ETF', None, 571.30),
    ('VOO', 'Vanguard S&P 500 ETF', 'ETF', None, 525.60),
    ('QQQ', 'Invesco QQQ Trust', 'ETF', None, 487.20),
    ('VTI', 'Vanguard Total Stock Market ETF', 'ETF', None, 282.40),
    ('IWM', 'iShares Russell 2000 ETF', 'ETF', None, 218.90),
    ('EFA', 'iShares MSCI EAFE ETF', 'ETF', None, 82.30),
    ('VEA', 'Vanguard FTSE Developed Markets ETF', 'ETF', None, 51.70),
    ('VWO', 'Vanguard FTSE Emerging Markets ETF', 'ETF', None, 46.80),
    ('SCHD', 'Schwab US Dividend Equity ETF', 'ETF', None, 28.40),
    ('VIG', 'Vanguard Dividend Appreciation ETF', 'ETF', None, 196.30),
    ('XLK', 'Technology Select Sector SPDR Fund', 'ETF', 'Technology', 228.10),
    ('XLV', 'Health Care Select Sector SPDR Fund', 'ETF', 'Health Care', 151.20),
    ('XLF', 'Financial Select Sector SPDR Fund', 'ETF', 'Financials', 46.30),
    ('AGG', 'iShares Core US Aggregate Bond ETF', 'ETF', None, 99.80),
    ('BND', 'Vanguard Total Bond Market ETF', 'ETF', None, 73.90),
    ('TLT', 'iShares 20+ Year Treasury Bond ETF', 'ETF', None, 94.60),
    ('LQD', 'iShares iBoxx Investment Grade Corporate Bond ETF', 'ETF', None, 109.20),
    ('GLD', 'SPDR Gold Shares', 'ETF', None, 243.50),
    ('UST-4.25-30', 'US Treasury Note 4.25% 2030', 'Bond', None, 1004.20),
    ('UST-3.875-33', 'US Treasury Note 3.875% 2033', 'Bond', None, 978.60),
    ('UST-4.50-34', 'US Treasury Note 4.50% 2034', 'Bond', None, 1012.40),
    ('UST-4.75-44', 'US Treasury Bond 4.75% 2044', 'Bond', None, 996.80),
    ('NYC-4.00-35', 'New York City GO 4.00% 2035', 'Bond', None, 1001.50),
    ('CA-3.50-32', 'State of California GO 3.50% 2032', 'Bond', None, 983.30),
    ('AAPL-3.35-32', 'Apple Inc. 3.35% Notes 2032', 'Bond', None, 962.70),
    ('JPM-4.60-34', 'JPMorgan Chase & Co. 4.60% Notes 2034', 'Bond', None, 991.40),
    ('MSFT-2.92-52', 'Microsoft Corp. 2.92% Notes 2052', 'Bond', None, 712.90),
    ('VZ-4.40-34', 'Verizon Communications 4.40% Notes 2034', 'Bond', None, 968.10),
]
NEVER_TRADED = {'SPG'}
BOND_ETFS = {'AGG', 'BND', 'TLT', 'LQD'}


# --------------------------------------------------------------------------- helpers
def q(v):
    if v is None:
        return 'NULL'
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    if isinstance(v, float):
        return f'{v:.4f}'.rstrip('0').rstrip('.') if abs(v) < 1 else f'{v:.2f}'
    return str(v)


def d(x):
    return x.isoformat()


def weekday_on_or_after(x):
    while x.weekday() >= 5:
        x += timedelta(days=1)
    return x


def add_business_days(x, n):
    while n:
        x += timedelta(days=1)
        if x.weekday() < 5:
            n -= 1
    return x


def settle(trade_date):
    if trade_date >= T1_START:
        return add_business_days(trade_date, 1)
    return add_business_days(trade_date, 2 if trade_date >= T2_START else 3)


def wchoice(items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


# --------------------------------------------------------------------------- price paths
# Factor model: every stock and equity ETF follows a shared market factor
# (scaled by its beta) plus its own noise; bonds and bond ETFs follow a shared
# interest-rate factor. Paths are built forward, then rescaled so each
# security ends exactly at its current_price. Prices only move on weekdays.
N_DAYS = (PRICE_DATE - FIRST_OPEN).days + 1
TD = 252
MKT_MU, MKT_VOL = 0.09, 0.16          # market: ~9% a year, 16% volatility
RATE_VOL = 0.045                      # 1x rate exposure: ~4.5% a year of price noise

# sector: (beta, idiosyncratic volatility)
SECTOR_RISK = {
    'Technology': (1.25, 0.24), 'Communication Services': (1.05, 0.22), 'Consumer Discretionary': (1.15, 0.23),
    'Consumer Staples': (0.60, 0.12), 'Health Care': (0.80, 0.17), 'Financials': (1.10, 0.17),
    'Industrials': (1.00, 0.17), 'Energy': (0.90, 0.24), 'Utilities': (0.50, 0.13),
    'Real Estate': (0.85, 0.16), 'Materials': (1.05, 0.21),
}
# ETFs and bonds: ticker -> (market beta, rate beta, own volatility, own drift)
FUND_RISK = {
    'SPY': (1.00, 0, 0.01, 0), 'VOO': (1.00, 0, 0.01, 0), 'VTI': (1.02, 0, 0.015, 0),
    'QQQ': (1.20, 0, 0.06, 0.02), 'IWM': (1.10, 0, 0.08, -0.02), 'EFA': (0.80, 0, 0.08, -0.03),
    'VEA': (0.80, 0, 0.08, -0.03), 'VWO': (0.75, 0, 0.12, -0.04), 'SCHD': (0.85, 0, 0.05, 0),
    'VIG': (0.85, 0, 0.04, 0), 'XLK': (1.20, 0, 0.06, 0.02), 'XLV': (0.80, 0, 0.07, 0),
    'XLF': (1.10, 0, 0.07, 0), 'GLD': (0.05, 0, 0.14, 0.03),
    'AGG': (0.00, 1.0, 0.005, 0.0), 'BND': (0.00, 1.0, 0.005, 0.0), 'LQD': (0.10, 1.3, 0.01, 0.0),
    'TLT': (0.00, 2.8, 0.01, -0.01),
    'UST-4.25-30': (0, 0.8, 0.003, 0), 'UST-3.875-33': (0, 1.4, 0.003, 0), 'UST-4.50-34': (0, 1.5, 0.003, 0),
    'UST-4.75-44': (0, 2.6, 0.004, 0), 'NYC-4.00-35': (0, 1.5, 0.006, 0), 'CA-3.50-32': (0, 1.2, 0.006, 0),
    'AAPL-3.35-32': (0.05, 1.2, 0.008, 0), 'JPM-4.60-34': (0.05, 1.4, 0.008, 0),
    'MSFT-2.92-52': (0.05, 3.0, 0.008, 0), 'VZ-4.40-34': (0.05, 1.4, 0.010, 0),
}

weekday = [(FIRST_OPEN + timedelta(days=i)).weekday() < 5 for i in range(N_DAYS)]
mkt = [rng.gauss(MKT_MU / TD, MKT_VOL / math.sqrt(TD)) if weekday[i] else 0.0 for i in range(N_DAYS)]
rate = [rng.gauss(0.0, RATE_VOL / math.sqrt(TD)) if weekday[i] else 0.0 for i in range(N_DAYS)]


def pin(series, total_log):
    # shift every trading day equally so the whole period ends at a realistic total
    n = sum(weekday)
    adj = (total_log - sum(series)) / n
    return [v + adj if weekday[i] else 0.0 for i, v in enumerate(series)]


mkt = pin(mkt, math.log(2.8))      # broad US market: about 2.8x from Jan 2015 to Oct 2026 (price only)
rate = pin(rate, math.log(0.92))   # core bonds: about -8% in price over the same period

paths = []
for ticker, name, cls, sector, price in SECURITIES:
    if ticker in FUND_RISK:
        beta, rbeta, vol, drift = FUND_RISK[ticker]
    else:
        beta, vol = SECTOR_RISK[sector]
        beta *= rng.uniform(0.85, 1.15)
        rbeta, drift = 0.0, rng.gauss(0.0, 0.04)
    d_mu, d_sd = drift / TD, vol / math.sqrt(TD)
    log_path, lp = [0.0] * N_DAYS, 0.0
    for i in range(1, N_DAYS):
        if weekday[i]:
            lp += beta * mkt[i] + rbeta * rate[i] + d_mu + rng.gauss(0.0, d_sd)
        log_path[i] = lp
    paths.append([price * math.exp(v - lp) for v in log_path])


def price_on(sec_idx, day):
    base = paths[sec_idx][(day - FIRST_OPEN).days]
    return round(base * (1 + rng.uniform(-0.003, 0.003)), 2)


def next_year_ratio(sec_idx, day):
    i = (day - FIRST_OPEN).days
    j = min(i + 365, N_DAYS - 1)
    return paths[sec_idx][j] / paths[sec_idx][i]


TRADABLE = [i for i, s in enumerate(SECURITIES) if s[0] not in NEVER_TRADED]
STOCKS = [i for i in TRADABLE if SECURITIES[i][2] == 'Equity']
EQ_ETFS = [i for i in TRADABLE if SECURITIES[i][2] == 'ETF' and SECURITIES[i][0] not in BOND_ETFS]
FI = [i for i in TRADABLE if SECURITIES[i][2] == 'Bond' or SECURITIES[i][0] in BOND_ETFS]
MIX = {'Growth': (0.72, 0.22, 0.06), 'Balanced': (0.45, 0.25, 0.30), 'Income': (0.18, 0.22, 0.60)}
DESK_TILT = {'Equity': (1.3, 1.0, 0.5), 'Fixed Income': (0.5, 0.8, 1.6), 'Multi-Asset': (1.0, 1.2, 1.0)}


def pick_security(strategy, manager, day, exclude=()):
    mix = MIX[strategy]
    tilt = DESK_TILT[MANAGERS[manager - 1][2]]
    w = [m * t for m, t in zip(mix, tilt)]
    bucket = wchoice([STOCKS, EQ_ETFS, FI], w)
    pool = [i for i in bucket if i not in exclude] or bucket
    skill = MANAGERS[manager - 1][6]
    weights = [max(next_year_ratio(i, day), 0.05) ** (skill * 2.0) for i in pool]
    return wchoice(pool, weights)


# --------------------------------------------------------------------------- clients, portfolios, owners
clients = []        # dicts
portfolios = []     # dicts
owners = []         # (portfolio_id, client_id, pct, added_date)
used_emails = set()


def new_client(first, last, born_from, born_to, risk=None):
    cid = len(clients) + 1
    base = f'{first}.{last}'.lower().replace(' ', '')
    email, n = f'{base}@example.com', 2
    while email in used_emails:
        email, n = f'{base}{n}@example.com', n + 1
    used_emails.add(email)
    dob = date(rng.randint(born_from, born_to), rng.randint(1, 12), rng.randint(1, 28))
    risk = risk or wchoice(['Conservative', 'Moderate', 'Aggressive'], [0.30, 0.45, 0.25])
    clients.append(dict(id=cid, first=first, last=last, email=email, dob=dob, risk=risk, onboard=None))
    return cid


def strategy_for(risk):
    return {'Conservative': wchoice(['Income', 'Balanced'], [0.7, 0.3]),
            'Moderate': wchoice(['Balanced', 'Growth', 'Income'], [0.6, 0.25, 0.15]),
            'Aggressive': wchoice(['Growth', 'Balanced'], [0.75, 0.25])}[risk]


DESK_FOR = {'Income': ['Fixed Income', 'Multi-Asset', 'Equity'], 'Balanced': ['Multi-Asset', 'Fixed Income', 'Equity'],
            'Growth': ['Equity', 'Multi-Asset', 'Fixed Income']}


def manager_for(strategy, open_date):
    desk = wchoice(DESK_FOR[strategy], [0.65, 0.25, 0.10])
    pool = [i + 1 for i, m in enumerate(MANAGERS)
            if m[2] == desk and i + 1 != NEW_HIRE and date.fromisoformat(m[3]) <= open_date]
    return rng.choice(pool)


def random_open_date():
    span = (date(2026, 10, 9) - FIRST_OPEN).days
    return weekday_on_or_after(FIRST_OPEN + timedelta(days=int(span * rng.random() ** 0.85)))


def opening_size():
    return max(100_000, min(60_000_000, round(rng.lognormvariate(math.log(1_600_000), 1.0), -3)))


def fee_for(size):
    if size >= 10_000_000:
        return 0.0060
    if size >= 5_000_000:
        return 0.0075
    if size >= 2_000_000:
        return 0.0085
    if size >= 1_000_000:
        return 0.0100
    return 0.0125


def new_portfolio(kind, owner_ids, pcts, name, open_date=None, size=None, strategy=None, manager=None, fee=None):
    pid = 101 + len(portfolios)
    open_date = open_date or random_open_date()
    lead = clients[owner_ids[0] - 1]
    strategy = strategy or strategy_for(lead['risk'])
    size = size or opening_size()
    manager = manager or manager_for(strategy, open_date)
    portfolios.append(dict(id=pid, manager=manager, name=name, type=kind, strategy=strategy,
                           fee=fee if fee is not None else fee_for(size), open=open_date, status='Active', size=size))
    for cid, pct in zip(owner_ids, pcts):
        owners.append((pid, cid, pct, open_date))
        c = clients[cid - 1]
        c['onboard'] = min(c['onboard'] or open_date, open_date)
    return pid


# Story household from the data dictionary: Elena and Daniel Ruiz, portfolio 101.
elena = new_client('Elena', 'Ruiz', 1978, 1978, 'Moderate')
clients[0]['dob'] = date(1978, 6, 21)
clients[0]['email'] = 'elena.ruiz@example.com'
daniel = new_client('Daniel', 'Ruiz', 1976, 1976, 'Moderate')
P101 = new_portfolio('Joint', [elena, daniel], [50.0, 50.0], 'Ruiz Family Growth', open_date=date(2025, 3, 12),
                     size=500_000, strategy='Growth', manager=1, fee=0.0100)

while len(portfolios) < N_PORTFOLIOS:
    roll = rng.random()
    last = rng.choice(LAST)
    if roll < 0.52:                                     # single person
        cid = new_client(rng.choice(FIRST), last, 1945, 1996)
        kind = wchoice(['Individual', 'IRA'], [0.7, 0.3])
        label = {'Individual': rng.choice(['Core', 'Personal', 'Investment']), 'IRA': 'IRA'}[kind]
        p = new_portfolio(kind, [cid], [100.0], f'{last} {label}')
        if rng.random() < 0.30 and len(portfolios) < N_PORTFOLIOS:
            other = 'IRA' if kind == 'Individual' else 'Individual'
            new_portfolio(other, [cid], [100.0], f'{last} {"IRA" if other == "IRA" else "Personal"}')
    elif roll < 0.88:                                   # couple
        yr = rng.randint(1948, 1992)
        a = new_client(rng.choice(FIRST), last, yr - 3, yr + 3)
        b = new_client(rng.choice(FIRST), last if rng.random() < 0.8 else rng.choice(LAST), yr - 3, yr + 3,
                       clients[a - 1]['risk'] if rng.random() < 0.7 else None)
        split = [50.0, 50.0] if rng.random() < 0.85 else [60.0, 40.0]
        new_portfolio('Joint', [a, b], split, f'{last} Joint')
        for person in (a, b):
            if rng.random() < 0.35 and len(portfolios) < N_PORTFOLIOS:
                new_portfolio('IRA', [person], [100.0], f'{clients[person - 1]["last"]} IRA')
            if rng.random() < 0.08 and len(portfolios) < N_PORTFOLIOS:
                new_portfolio('Individual', [person], [100.0], f'{clients[person - 1]["last"]} Personal')
    else:                                               # family trust
        n = rng.choice([2, 3, 3, 4])
        yr = rng.randint(1945, 1965)
        members = [new_client(rng.choice(FIRST), last, yr - 2, yr + 2)]
        for _ in range(n - 1):
            members.append(new_client(rng.choice(FIRST), last, yr + 22, yr + 38))
        split = {2: [60.0, 40.0], 3: [40.0, 30.0, 30.0], 4: [40.0, 20.0, 20.0, 20.0]}[n]
        new_portfolio('Trust', members, split, f'{last} Family Trust')
        if n >= 3 and rng.random() < 0.5 and len(portfolios) < N_PORTFOLIOS:
            new_portfolio('Joint', members[:2], [50.0, 50.0], f'{last} Joint')
portfolios = portfolios[:N_PORTFOLIOS]
valid_pids = {p['id'] for p in portfolios}
owners = [o for o in owners if o[0] in valid_pids]
owned = {o[1] for o in owners}
clients = [c for c in clients if c['id'] in owned]           # drop anyone left without a portfolio
assert [c['id'] for c in clients] == list(range(1, len(clients) + 1)), 'client ids must stay contiguous'

# A few brand-new accounts: funded in October 2026, no trades yet.
for p in portfolios[-3:]:
    p['open'] = weekday_on_or_after(date(2026, 10, rng.randint(12, 14)))
    p['no_trades'] = True
for i, o in enumerate(owners):
    p = next(x for x in portfolios if x['id'] == o[0])
    if o[3] != p['open']:
        owners[i] = (o[0], o[1], o[2], p['open'])
for c in clients:
    c['onboard'] = min(o[3] for o in owners if o[1] == c['id'])

# Attrition: each portfolio has about a 2% chance a year of being closed.
for p in portfolios:
    days_open = (LAST_TRADE - p['open']).days
    if p['id'] == P101 or p.get('no_trades') or days_open < 400:
        continue
    if rng.random() < 1 - 0.98 ** (days_open / 365):
        p['close'] = weekday_on_or_after(p['open'] + timedelta(days=rng.randint(200, days_open - 5)))
        p['status'] = 'Closed'

# --------------------------------------------------------------------------- simulate cash flows and trades
flows = []    # dict(pid, cid, date, type, amount)
trades = []   # dict(pid, sec, broker, date, side, qty, price)
BROKER_IDS = [i + 1 for i, b in enumerate(BROKERS) if b[4] == 1]
BROKER_W = [BROKERS[i - 1][5] for i in BROKER_IDS]


def simulate(p):
    pid, strat, mgr = p['id'], p['strategy'], p['manager']
    own = [(o[1], o[2]) for o in owners if o[0] == pid]
    hold = {}
    cash = 0.0
    end = p.get('close', LAST_TRADE)
    cursor = p['open']          # events in a portfolio never go back in time

    def buy(day, sec, budget, broker=None, qty=None, price=None):
        nonlocal cash, cursor
        cursor = max(cursor, day)
        broker = broker or wchoice(BROKER_IDS, BROKER_W)
        price = price or price_on(sec, day)
        rate = BROKERS[broker - 1][3]
        qty = qty or int(budget // (price * (1 + rate)))
        cost = qty * price * (1 + rate)
        if qty < 1 or cost > cash + 1e-6:
            return False
        cash -= cost
        hold[sec] = hold.get(sec, 0) + qty
        trades.append(dict(pid=pid, sec=sec, broker=broker, date=day, side='Buy', qty=qty, price=price))
        return True

    def sell(day, sec, qty):
        nonlocal cash, cursor
        cursor = max(cursor, day)
        qty = min(qty, hold.get(sec, 0))
        if qty < 1:
            return
        broker = wchoice(BROKER_IDS, BROKER_W)
        price = price_on(sec, day)
        cash += qty * price * (1 - BROKERS[broker - 1][3])
        hold[sec] -= qty
        if hold[sec] == 0:
            del hold[sec]
        trades.append(dict(pid=pid, sec=sec, broker=broker, date=day, side='Sell', qty=qty, price=price))

    def value(day):
        return cash + sum(q_ * paths[s][(day - FIRST_OPEN).days] for s, q_ in hold.items())

    # opening deposits, one per owner, sized by ownership share
    dep_day = weekday_on_or_after(p['open'] + timedelta(days=rng.randint(0, 3)))
    for cid, pct in own:
        amt = round(p['size'] * pct / 100, 2)
        if pid == P101:
            amt = 250000.00
            dep_day = date(2025, 3, 15)
        flows.append(dict(pid=pid, cid=cid, date=dep_day, type='Deposit', amount=amt))
        cash += amt
    if p.get('no_trades'):
        p['end_value'] = p['net_in'] = cash    # funded, nothing bought yet
        return

    # initial build-out: 5-9 positions using ~90% of cash
    day = weekday_on_or_after(dep_day + timedelta(days=rng.randint(2, 6)))
    n_pos = rng.randint(5, 9)
    picks = []
    for _ in range(n_pos):
        picks.append(pick_security(strat, mgr, day, exclude=picks))
    invest = cash * rng.uniform(0.86, 0.95)
    for sec in picks:
        buy(day, sec, invest / n_pos)

    # month by month: rebalance trades, contributions, withdrawals
    month = date(day.year, day.month, 1)
    special_done = False
    while True:
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
        if month > end:
            break
        last_day = min(end, date(month.year + (month.month == 12), month.month % 12 + 1, 1) - timedelta(days=1))

        def when():
            t_ = weekday_on_or_after(month + timedelta(days=rng.randint(0, max(0, (last_day - month).days - 3))))
            return min(max(t_, cursor), end)

        if pid == P101 and not special_done and month == date(2026, 9, 1):
            flows.append(dict(pid=pid, cid=elena, date=date(2026, 9, 10), type='Deposit', amount=50000.00))
            cash += 50000.00
            aapl = next(i for i, s in enumerate(SECURITIES) if s[0] == 'AAPL')
            assert buy(date(2026, 9, 15), aapl, 0, broker=2, qty=200,
                       price=round(paths[aapl][(date(2026, 9, 15) - FIRST_OPEN).days], 2))
            trades[-1]['special'] = True
            special_done = True

        if rng.random() < 0.05:                                   # contribution, then invest it
            cid = wchoice([o[0] for o in own], [o[1] for o in own])
            t = when()
            if t <= end:
                amt = round(value(t) * rng.uniform(0.03, 0.15), -2)
                flows.append(dict(pid=pid, cid=cid, date=t, type='Deposit', amount=amt))
                cash += amt
                t2 = weekday_on_or_after(t + timedelta(days=rng.randint(1, 5)))
                if t2 <= end:
                    buy(t2, pick_security(strat, mgr, t2), amt * 0.95)

        if rng.random() < 0.11 and hold:                          # rebalance: trim one, add one
            t = when()
            sec = rng.choice(list(hold))
            sell(t, sec, max(1, int(hold[sec] * rng.choice([0.25, 0.5, 0.5, 1.0]))))
            if rng.random() < 0.85:
                buy(t, pick_security(strat, mgr, t, exclude=[sec]), cash * rng.uniform(0.6, 0.95))

        if rng.random() < 0.05:                                   # withdrawal (sell first if needed)
            t = when()
            amt = round(value(t) * rng.uniform(0.02, 0.08), -2)
            while cash < amt and hold:
                sec = max(hold, key=lambda s: hold[s] * paths[s][(t - FIRST_OPEN).days])
                sell(t, sec, max(1, hold[sec] // 2))
            if 0 < amt <= cash:
                cid = wchoice([o[0] for o in own], [o[1] for o in own])
                flows.append(dict(pid=pid, cid=cid, date=t, type='Withdrawal', amount=amt))
                cash -= amt

    if 'close' in p:                                              # liquidate and pay out to owners
        t = p['close']
        for sec in list(hold):
            sell(t, sec, hold[sec])
        payout_day = add_business_days(t, 2)
        remaining = cash
        for k, (cid, pct) in enumerate(own):
            amt = round(cash * pct / 100, 2) if k < len(own) - 1 else round(remaining, 2)
            remaining -= amt
            if amt > 0:
                flows.append(dict(pid=pid, cid=cid, date=payout_day, type='Withdrawal', amount=amt))
        cash = 0.0
    p['end_cash'] = cash
    p['end_value'] = cash + sum(q_ * SECURITIES[s_][4] for s_, q_ in hold.items())
    p['net_in'] = sum(f['amount'] if f['type'] == 'Deposit' else -f['amount'] for f in flows if f['pid'] == pid)


for p in portfolios:
    simulate(p)

# order rows chronologically, keeping the dictionary's story rows as id 1
flows.sort(key=lambda f: (f['date'], f['pid'], f['cid']))
first_flow = next(f for f in flows if f['pid'] == P101 and f['cid'] == elena)
flows.remove(first_flow)
flows.insert(0, first_flow)
trades.sort(key=lambda t: (t['date'], t['pid'], t['side'] != 'Sell'))
special = next(t for t in trades if t.get('special'))
trades.remove(special)
trades.insert(0, special)

# broker confirmation numbers: prefix + running number, unique (rule 6)
counters = {i + 1: 10000 for i in range(len(BROKERS))}
for t in trades:
    if t.get('special'):
        t['conf'] = 'GS-10482'
        continue
    counters[t['broker']] += 1
    if t['broker'] == 2 and counters[2] == 10482:
        counters[2] += 1
    t['conf'] = f"{BROKERS[t['broker'] - 1][1]}-{counters[t['broker']]}"

# --------------------------------------------------------------------------- invariants
for p in portfolios:
    assert abs(sum(o[2] for o in owners if o[0] == p['id']) - 100) < 1e-9
pos = {}
for t in sorted(trades, key=lambda t: (t['date'], t['side'] != 'Buy')):
    k = (t['pid'], t['sec'])
    pos[k] = pos.get(k, 0) + (t['qty'] if t['side'] == 'Buy' else -t['qty'])
    assert pos[k] >= 0, ('oversold', k)
assert len({t['conf'] for t in trades}) == len(trades)
own_set = {(o[0], o[1]) for o in owners}
assert all((f['pid'], f['cid']) in own_set for f in flows)
assert all(f['amount'] > 0 for f in flows)

# --------------------------------------------------------------------------- write SQL
SCHEMA = """PRAGMA foreign_keys = ON;   -- SQLite enforces FKs only when this is on

-- Clean slate so the script can be re-run (children first)
DROP TABLE IF EXISTS trade;
DROP TABLE IF EXISTS cash_flow;
DROP TABLE IF EXISTS portfolio_owner;
DROP TABLE IF EXISTS portfolio;
DROP TABLE IF EXISTS broker;
DROP TABLE IF EXISTS security;
DROP TABLE IF EXISTS portfolio_manager;
DROP TABLE IF EXISTS client;

-- ---------------------------------------------------------------------
-- PART 1: CREATE (structure + business rules as constraints)
-- ---------------------------------------------------------------------

-- Client (7 columns)
CREATE TABLE client (
    client_id      INTEGER PRIMARY KEY,
    first_name     TEXT    NOT NULL,
    last_name      TEXT    NOT NULL,
    email          TEXT    NOT NULL UNIQUE,
    date_of_birth  TEXT    NOT NULL,
    risk_profile   TEXT    NOT NULL
                   CHECK (risk_profile IN ('Conservative','Moderate','Aggressive')),
    onboard_date   TEXT    NOT NULL DEFAULT (date('now'))
);

-- Portfolio_Manager (8 columns)
-- Rule 11: profit share is a rate between 0 and 1 (0.03 = 3%).
CREATE TABLE portfolio_manager (
    manager_id        INTEGER PRIMARY KEY,
    first_name        TEXT    NOT NULL,
    last_name         TEXT    NOT NULL,
    email             TEXT    NOT NULL UNIQUE,
    desk              TEXT    NOT NULL
                      CHECK (desk IN ('Equity','Fixed Income','Multi-Asset')),
    hire_date         TEXT    NOT NULL,
    base_salary       REAL    NOT NULL CHECK (base_salary > 0),
    profit_share_pct  REAL    NOT NULL CHECK (profit_share_pct BETWEEN 0 AND 1)
);

-- Portfolio (8 columns)
-- Rule 1: each portfolio must be managed by exactly one manager (FK NOT NULL);
--         a manager may manage many portfolios.
-- Rule 11: fee_pct is a rate between 0 and 1 (0.01 = 1%).
CREATE TABLE portfolio (
    portfolio_id    INTEGER PRIMARY KEY,
    manager_id      INTEGER NOT NULL,
    portfolio_name  TEXT    NOT NULL,
    account_type    TEXT    NOT NULL
                    CHECK (account_type IN ('Individual','Joint','IRA','Trust')),
    strategy        TEXT    NOT NULL
                    CHECK (strategy IN ('Growth','Income','Balanced')),
    fee_pct         REAL    NOT NULL CHECK (fee_pct BETWEEN 0 AND 1),
    open_date       TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'Active'
                    CHECK (status IN ('Active','Closed')),
    FOREIGN KEY (manager_id) REFERENCES portfolio_manager(manager_id)
);

-- Portfolio_Owner (4 columns) - associative table resolving the client-portfolio M:N
-- Rule 2: a client may own many portfolios and a portfolio may have many owners.
--         (Every portfolio having at least one owner is enforced by the application.)
-- Rule 8: ownership_pct is greater than 0 and no more than 100. It lives HERE
--         because it depends on BOTH the client and the portfolio.
CREATE TABLE portfolio_owner (
    portfolio_id   INTEGER NOT NULL,
    client_id      INTEGER NOT NULL,
    ownership_pct  REAL    NOT NULL CHECK (ownership_pct > 0 AND ownership_pct <= 100),
    added_date     TEXT    NOT NULL DEFAULT (date('now')),
    PRIMARY KEY (portfolio_id, client_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolio(portfolio_id),
    FOREIGN KEY (client_id)    REFERENCES client(client_id)
);

-- Cash_Flow (6 columns)
-- Rules 5a/5b: each deposit or withdrawal is made by exactly one client into exactly
--              one portfolio, and that client must OWN the portfolio. One composite
--              FK to portfolio_owner enforces both at once.
-- Rule 10: flow_type is Deposit or Withdrawal, and amount is greater than zero.
CREATE TABLE cash_flow (
    flow_id       INTEGER PRIMARY KEY,
    portfolio_id  INTEGER NOT NULL,
    client_id     INTEGER NOT NULL,
    flow_date     TEXT    NOT NULL,
    flow_type     TEXT    NOT NULL CHECK (flow_type IN ('Deposit','Withdrawal')),
    amount        REAL    NOT NULL CHECK (amount > 0),
    FOREIGN KEY (portfolio_id, client_id)
        REFERENCES portfolio_owner(portfolio_id, client_id)
);

-- Security (7 columns)
-- Only today's price is stored (current_price as of price_date); no price history.
CREATE TABLE security (
    security_id    INTEGER PRIMARY KEY,
    ticker         TEXT    NOT NULL UNIQUE,
    security_name  TEXT    NOT NULL,
    asset_class    TEXT    NOT NULL CHECK (asset_class IN ('Equity','ETF','Bond')),
    sector         TEXT,
    current_price  REAL    NOT NULL CHECK (current_price > 0),
    price_date     TEXT    NOT NULL
);

-- Broker (5 columns)
-- Rule 11: commission_rate is a rate between 0 and 1 (0.0005 = 0.05%).
CREATE TABLE broker (
    broker_id        INTEGER PRIMARY KEY,
    broker_name      TEXT    NOT NULL UNIQUE,
    contact_email    TEXT,
    commission_rate  REAL    NOT NULL CHECK (commission_rate BETWEEN 0 AND 1),
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

-- Trade (10 columns)
-- Rules 3a/3b/4: each trade is for exactly one portfolio and one security, and is
--                executed by exactly one broker (all FKs NOT NULL).
-- Rule 6: confirmation_no is unique, so the same trade cannot be entered twice.
-- Rule 7: side is Buy or Sell; quantity and price are greater than zero.
-- Rule 9: settlement cannot be earlier than the trade date.
-- Note: no "commission" column - it is quantity x price x broker.commission_rate,
--       so storing it would create an update anomaly.
CREATE TABLE trade (
    trade_id         INTEGER PRIMARY KEY,
    confirmation_no  TEXT    NOT NULL UNIQUE,
    portfolio_id     INTEGER NOT NULL,
    security_id      INTEGER NOT NULL,
    broker_id        INTEGER NOT NULL,
    trade_date       TEXT    NOT NULL,
    side             TEXT    NOT NULL CHECK (side IN ('Buy','Sell')),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    price            REAL    NOT NULL CHECK (price > 0),
    settlement_date  TEXT    NOT NULL,
    CHECK (settlement_date >= trade_date),
    FOREIGN KEY (portfolio_id) REFERENCES portfolio(portfolio_id),
    FOREIGN KEY (security_id)  REFERENCES security(security_id),
    FOREIGN KEY (broker_id)    REFERENCES broker(broker_id)
);
"""


def inserts(table, cols, rows, chunk=500):
    out = []
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n" +
                   ',\n'.join(' (' + ', '.join(q(v) for v in r) + ')' for r in part) + ';')
    return '\n'.join(out)


def money(x):
    return float(f'{x:.2f}')


rows_client = [(c['id'], c['first'], c['last'], c['email'], d(c['dob']), c['risk'], d(c['onboard'])) for c in clients]
rows_mgr = [(i + 1, m[0], m[1], f'{m[0][0].lower()}.{m[1].lower()}@royalpointcap.example', m[2], m[3],
             float(m[4]), m[5]) for i, m in enumerate(MANAGERS)]
rows_port = [(p['id'], p['manager'], p['name'], p['type'], p['strategy'], p['fee'], d(p['open']), p['status'])
             for p in portfolios]
rows_owner = [(o[0], o[1], o[2], d(o[3])) for o in owners]
rows_flow = [(i + 1, f['pid'], f['cid'], d(f['date']), f['type'], money(f['amount'])) for i, f in enumerate(flows)]
rows_sec = [(i + 1, s[0], s[1], s[2], s[3], s[4], d(PRICE_DATE)) for i, s in enumerate(SECURITIES)]
rows_brk = [(i + 1, b[0], b[2], b[3], b[4]) for i, b in enumerate(BROKERS)]
rows_trade = [(i + 1, t['conf'], t['pid'], t['sec'] + 1, t['broker'], d(t['date']), t['side'], t['qty'],
               money(t['price']), d(settle(t['date']))) for i, t in enumerate(trades)]

# facts used in the story comments below
N_CLOSED = sum(p['status'] == 'Closed' for p in portfolios)
NO_TRADE_IDS = [p['id'] for p in portfolios if p.get('no_trades')]
_mgr_profit = {}
for p in portfolios:
    _mgr_profit[p['manager']] = _mgr_profit.get(p['manager'], 0) + p['end_value'] - p['net_in']
LOSERS = [f'{MANAGERS[m - 1][0]} {MANAGERS[m - 1][1]} ({m})' for m in sorted(_mgr_profit) if _mgr_profit[m] < 0]
FIRST_YEAR = min(p['open'] for p in portfolios).year
SETTLE_NOTE = 'Settlement is T+3 before 2017-09-05, T+2 until 2024-05-28 and T+1 after.'

counts = [('client', len(rows_client)), ('portfolio_manager', len(rows_mgr)), ('portfolio', len(rows_port)),
          ('portfolio_owner', len(rows_owner)), ('cash_flow', len(rows_flow)), ('security', len(rows_sec)),
          ('broker', len(rows_brk)), ('trade', len(rows_trade))]
total = sum(n for _, n in counts)
header = f"""-- =====================================================================
-- BAN-0301 | A1.1 Royal Point Capital: client portfolio management
-- One regional office: 15 portfolio managers, 600 client portfolios (book since 2015).
-- Runs in DB Browser for SQLite: open a new database, then
-- Execute SQL > paste (or open) this whole script > Run (Ctrl/Cmd + Return).
--
-- Size check: 8 tables, 55 columns, {total:,} sample rows:
""" + '\n'.join(f'--   {n:<18} {c:>6,} rows' for n, c in counts) + """
--
-- Sample data is simulated by generate_royal_point_data.py (fixed seed),
-- so it obeys every business rule. All amounts are USD; prices are per unit.
-- =====================================================================

"""

body = [header, SCHEMA,
        '-- ---------------------------------------------------------------------',
        '-- PART 2: LOAD (sample data - parents before children)',
        '-- No BEGIN/COMMIT here: DB Browser already wraps Execute SQL in a transaction.',
        '-- Click Write Changes (Ctrl/Cmd + S) afterwards to save the data to disk.',
        '-- ---------------------------------------------------------------------', '',
        '-- 15 managers across three desks. Manager 6 is a new hire with no portfolios yet.',
        inserts('portfolio_manager', ['manager_id', 'first_name', 'last_name', 'email', 'desk', 'hire_date',
                                      'base_salary', 'profit_share_pct'], rows_mgr), '',
        '-- 6 brokers; Old Quay Securities (6) is inactive and has no trades.',
        inserts('broker', ['broker_id', 'broker_name', 'contact_email', 'commission_rate', 'is_active'], rows_brk), '',
        '-- 120 approved securities (92 stocks, 18 ETFs, 10 bonds). SPG is approved but never traded.',
        inserts('security', ['security_id', 'ticker', 'security_name', 'asset_class', 'sector', 'current_price',
                             'price_date'], rows_sec), '',
        f'-- {len(rows_client)} clients. Client 1 (Elena Ruiz) and 2 (Daniel Ruiz) are the data-dictionary examples.',
        inserts('client', ['client_id', 'first_name', 'last_name', 'email', 'date_of_birth', 'risk_profile',
                           'onboard_date'], rows_client), '',
        f'-- {len(rows_port)} portfolios (ids 101-{100 + len(rows_port)}). The last three were funded in October 2026',
        f'-- and have no trades yet; {N_CLOSED} portfolios were closed over the years.',
        inserts('portfolio', ['portfolio_id', 'manager_id', 'portfolio_name', 'account_type', 'strategy', 'fee_pct',
                              'open_date', 'status'], rows_port), '',
        f'-- {len(rows_owner)} ownership rows: single owners at 100%, joint accounts at 50/50 or 60/40,',
        '-- family trusts split across 2-4 owners. Each portfolio adds up to 100%.',
        inserts('portfolio_owner', ['portfolio_id', 'client_id', 'ownership_pct', 'added_date'], rows_owner), '',
        f'-- {len(rows_flow)} deposits and withdrawals, each made by an owner of the portfolio.',
        inserts('cash_flow', ['flow_id', 'portfolio_id', 'client_id', 'flow_date', 'flow_type', 'amount'],
                rows_flow), '',
        f'-- {len(rows_trade)} trades. {SETTLE_NOTE}',
        inserts('trade', ['trade_id', 'confirmation_no', 'portfolio_id', 'security_id', 'broker_id', 'trade_date',
                          'side', 'quantity', 'price', 'settlement_date'], rows_trade), '',
        '']


# --------------------------------------------------------------------------- 02_load.sql (Build worksheet)
# Same rows, INSERTs only, in the same table order as 01_create.sql.
load_header = f"""PRAGMA foreign_keys = ON;   -- SQLite enforces FKs only when this is on

-- =====================================================================
-- BAN-0301 | A1.1 Royal Point Capital: 02_load.sql
-- Fills the 8 tables built by 01_create.sql with {total:,} sample rows for one
-- regional office: 15 managers, 600 portfolios opened since {FIRST_YEAR},
-- {len(rows_trade):,} trades.
""" + '\n'.join(f'--   {n:<18} {c:>6,} rows' for n, c in counts) + f"""
--
-- Run 01_create.sql first. Then: Execute SQL tab > open this file > Run,
-- then Write Changes (Ctrl/Cmd + S). No BEGIN/COMMIT: DB Browser already
-- wraps Execute SQL in a transaction.
--
-- Data is simulated by generate_royal_point_data.py (fixed seed), so every
-- row obeys the business rules. All amounts are USD; prices are per unit.
--
-- Story rows (what makes the demo queries show something):
--   * Elena (1) and Daniel (2) Ruiz co-own portfolio 101 at 50/50: the M:N
--     and ownership_pct on the associative table. Trade 1 is their AAPL buy.
--   * Manager 6, Gabriela Santos, is a new hire with no portfolios: a LEFT
--     JOIN shows her with $0 profit and pay = base salary only.
--   * Old Quay Securities (broker 6) is inactive with no trades, and SPG is
--     approved but never traded: LEFT JOINs that return zero.
--   * {N_CLOSED} portfolios are Closed (fully sold, cash paid out to the owners), so
--     a WHERE on status filters something out.
--   * Portfolios {NO_TRADE_IDS[0]}-{NO_TRADE_IDS[-1]} were funded in October 2026 but have no trades yet.
--   * {' and '.join(LOSERS)} lost money for clients overall, so the
--     MAX(0, profit) floor on profit share kicks in.
--   * Optional columns left NULL: Lakeshore's contact_email, and sector on
--     bonds and broad-market ETFs.
-- =====================================================================

-- Clean slate so the script can be re-run (children first)
DELETE FROM cash_flow;
DELETE FROM portfolio_owner;
DELETE FROM trade;
DELETE FROM portfolio;
DELETE FROM broker;
DELETE FROM security;
DELETE FROM portfolio_manager;
DELETE FROM client;

"""
load_body = [load_header,
             '-- ---------------------------------------------------------------------',
             '-- STEP 1: tables with no foreign keys',
             '-- ---------------------------------------------------------------------', '',
             f'-- {len(rows_client)} clients. Client 1 (Elena Ruiz) and 2 (Daniel Ruiz) are the data-dictionary examples.',
             inserts('client', ['client_id', 'first_name', 'last_name', 'email', 'date_of_birth', 'risk_profile',
                                'onboard_date'], rows_client), '',
             '-- 15 managers across three desks. Manager 6 is a new hire with no portfolios yet.',
             inserts('portfolio_manager', ['manager_id', 'first_name', 'last_name', 'email', 'desk', 'hire_date',
                                           'base_salary', 'profit_share_pct'], rows_mgr), '',
             '-- 120 approved securities (92 stocks, 18 ETFs, 10 bonds). SPG is approved but never traded.',
             inserts('security', ['security_id', 'ticker', 'security_name', 'asset_class', 'sector', 'current_price',
                                  'price_date'], rows_sec), '',
             '-- 6 brokers; Old Quay Securities (6) is inactive and has no trades.',
             inserts('broker', ['broker_id', 'broker_name', 'contact_email', 'commission_rate', 'is_active'],
                     rows_brk), '',
             '-- ---------------------------------------------------------------------',
             '-- STEP 2: tables that point at step 1',
             '-- ---------------------------------------------------------------------', '',
             f'-- {len(rows_port)} portfolios (ids 101-{100 + len(rows_port)}). The last three were funded in October 2026',
             f'-- and have no trades yet; {N_CLOSED} portfolios were closed over the years.',
             inserts('portfolio', ['portfolio_id', 'manager_id', 'portfolio_name', 'account_type', 'strategy',
                                   'fee_pct', 'open_date', 'status'], rows_port), '',
             f'-- {len(rows_trade)} trades. {SETTLE_NOTE}',
             inserts('trade', ['trade_id', 'confirmation_no', 'portfolio_id', 'security_id', 'broker_id',
                               'trade_date', 'side', 'quantity', 'price', 'settlement_date'], rows_trade), '',
             '-- ---------------------------------------------------------------------',
             '-- STEP 3: the associative table, and the table that points at it',
             '-- ---------------------------------------------------------------------', '',
             f'-- {len(rows_owner)} ownership rows: single owners at 100%, joint accounts at 50/50 or 60/40,',
             '-- family trusts split across 2-4 owners. Each portfolio adds up to 100%.',
             inserts('portfolio_owner', ['portfolio_id', 'client_id', 'ownership_pct', 'added_date'], rows_owner), '',
             f'-- {len(rows_flow)} deposits and withdrawals, each made by an owner of the portfolio.',
             inserts('cash_flow', ['flow_id', 'portfolio_id', 'client_id', 'flow_date', 'flow_type', 'amount'],
                     rows_flow), '',
             '']
with open(LOAD_OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(load_body))

for n, c in counts:
    print(f'{n:<18} {c:>6,}')
print(f'{"total":<18} {total:>6,}')
