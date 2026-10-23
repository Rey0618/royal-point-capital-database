# Royal Point Capital — Client Portfolio Management Database

A relational database designed and built in SQLite for one regional office of **Royal Point Capital**, an invented investment management firm. It records who owns each client portfolio (including joint and family accounts), every deposit and withdrawal, and every trade placed through outside brokers. From those stored facts it calculates holdings, portfolio value, profit, management fees, manager pay and broker commissions.

Built for **BAN-0301: Managing Structured Data with SQL** (Hult International Business School), assignment A1.1: *Database design and implementation*.

| | |
|---|---|
| **Engine** | SQLite (tested in DB Browser for SQLite and the `sqlite3` CLI) |
| **Schema** | 8 tables, 55 columns, 16 business rules |
| **Sample data** | 22,153 simulated rows: 15 managers, 600 portfolios (537 active), 615 clients, 15,405 trades, 2015–2026 |
| **Report** | [Markdown](report/Royal_Point_Capital_A1.1_Report.md) · Word (APA 7): `report/Royal_Point_Capital_A1.1_Report.docx` |

---

## Repository structure

```
royal-point-capital-database/
├── README.md
├── report/
│   ├── Royal_Point_Capital_A1.1_Report.md      # full report (renders on GitHub)
│   └── Royal_Point_Capital_A1.1_Report.docx    # APA 7 version for submission
├── sql/
│   ├── 01_create.sql          # builds the 8 tables with all constraints
│   ├── 02_load.sql            # loads 22,153 rows of sample data
│   ├── 03_demonstrate.sql     # build checks, business queries, rule tests, filtered samples
│   └── general_queries.sql    # exploratory analysis of the branch (not graded)
├── data_dictionary/
│   └── Royal_Point_Capital_Logical_Data_Dictionary.xlsx   # one tab per table
├── diagrams/
│   ├── figure1_conceptual_model.png
│   ├── figure2_logical_model.png
│   └── source/                # SVG sources and an early draw.io sketch
└── scripts/
    ├── generate_royal_point_data.py   # regenerates sql/02_load.sql (fixed seed)
    └── draw_erd.py                    # regenerates the ER diagrams as SVG
```

## Quick start

### DB Browser for SQLite
1. **New Database**, then save it as `royal_point.db`. Cancel the "Edit table definition" window.
2. In the **Execute SQL** tab, open and run each script in order:
   `sql/01_create.sql` → `sql/02_load.sql` → `sql/03_demonstrate.sql`.
3. Click **Write Changes** (Ctrl/Cmd + S) to save.

### Command line
```bash
sqlite3 royal_point.db < sql/01_create.sql
```
```bash
sqlite3 royal_point.db < sql/02_load.sql
```
```bash
sqlite3 -header -column royal_point.db < sql/03_demonstrate.sql
```

Every script starts with `PRAGMA foreign_keys = ON;`. All three run with no errors on a brand-new database, and every script can be re-run safely: `01` drops and recreates the tables, and `02` deletes the existing rows before loading.

## Data model

![Logical data model](diagrams/figure2_logical_model.png)

| Table | Purpose |
|---|---|
| `client` | People who own portfolios |
| `portfolio_manager` | Managers, their desk and pay terms |
| `portfolio` | Investment accounts: type, strategy, fee, status |
| `portfolio_owner` | **Associative table** for the client ↔ portfolio many-to-many. Holds each owner's `ownership_pct` |
| `cash_flow` | Deposits and withdrawals. Its **composite foreign key** to `portfolio_owner` means only an owner can move money |
| `security` | Approved stocks, ETFs and bonds, with today's price |
| `broker` | Outside brokers and their commission rates |
| `trade` | Every buy and sell. The unique `confirmation_no` stops a trade from being entered twice |

The design follows third normal form. Values that can be derived are **calculated in queries, never stored**: commission, holdings, cash balance, portfolio value, profit, fees and manager pay. See the [report](report/Royal_Point_Capital_A1.1_Report.md) for the business rules, the conceptual model and the reasoning behind the normalization.

## What `03_demonstrate.sql` shows

| Part | Contents |
|---|---|
| **A: build checks** | 8 tables and 55 columns, row counts, foreign keys on, no orphan rows |
| **B: business questions** | **Q1** holdings, value and profit per portfolio. **Q2** manager pay (base salary + profit share, floored at 0). **Q3** fee revenue vs. manager pay, and commissions by broker. Two views (`v_holdings`, `v_portfolio_value`) do the math once. |
| **C: rule tests** | Seven statements, commented out, that each break a rule (NOT NULL, FOREIGN KEY, CHECK, UNIQUE). Run each one alone and it fails with the expected error. |
| **D: filtered samples** | One `WHERE`-filtered query per table |

Headline results from the sample data:
- **Size:** $2.62B under management in 537 active portfolios.
- **Fees vs. pay:** about $21.2M a year in fees against $6.8M of manager pay, which is 32% of revenue.
- **Market benchmarks:** the S&P 500 ETF is up about 134% since 2015 and the core bond ETF is down about 7%.

## Sample data

The data is **simulated**, not taken from a real firm. `scripts/generate_royal_point_data.py` (Python standard library only, fixed seed 301) recreates `sql/02_load.sql` exactly:

```bash
python3 scripts/generate_royal_point_data.py
```

The simulation works like a real office, month by month:

- **Accounts:** households open individual, joint, IRA and trust accounts.
- **Activity:** owners deposit and withdraw money, and managers buy, rebalance and sell.
- **Prices:** prices follow a shared market factor and an interest-rate factor.
- **Settlement:** follows the US rules of the time: T+3, then T+2, then T+1.

Before it writes anything, the script checks that:

- no sale is larger than the shares held
- cash never goes negative
- each portfolio's ownership adds up to 100%
- every cash flow comes from an owner
- confirmation numbers are unique

It also builds in *story rows* that make the queries interesting: a jointly owned portfolio (101), a new manager with no clients yet, an inactive broker, a security that was never traded, closed portfolios, and a manager whose clients lost money.

## Assumptions and limits

- Only **today's price** is stored (`security.current_price` as of 2026-10-16). There is no price history, so returns are measured since each portfolio opened.
- All amounts are in **USD**. Prices are per unit. Dividends and bond interest are not tracked.
- Fee, profit-share and commission rates are assumed fixed over the period.
- Rule 2 (every portfolio has at least one owner) and ownership summing to 100% are enforced by the application, not by SQLite constraints.

## AI use

Claude (Anthropic) assisted with drafting text, checking the design against the assignment, generating the simulated data, drawing the diagrams, and drafting and testing the SQL. The author reviewed all design decisions and results. See the disclosure section of the report.

## License

Released under the [MIT License](LICENSE).

## Author

**Reynaldo Garcia**, Hult International Business School (Fall 2026).
