# Overnight risk premium — Nasdaq-100 futures

Reproducible check of the overnight (16:00 → 09:00 ET) return in Nasdaq-100
index futures, plus a forward account simulation under a fixed trailing
drawdown and a percentage-giveback loss limit.

Everything below reproduces from a clean checkout — data is included.

## Data (`data/`)

Three files, one row per trading night, aligned on the entry date. The strategy
holds Nasdaq-100 futures overnight — **enter at 16:00 ET** (the US cash close),
**exit at 09:00 ET** the next morning (30 min before the 09:30 open).

| file | span | rows |
|---|---|---|
| `ndx_cache.csv` | 2010-01-04 … 2026-08-17 | 4180 |
| `overnight_path2.parquet` | 2014-11-11 … 2026-07-31 | 2891 |
| `overnight_pct.parquet` | 2014-11-11 … 2026-08-03 | 2898 |

### Where it comes from

- **`ndx_cache.csv`** — Nasdaq-100 **index** (^NDX) daily close, from Yahoo
  Finance (`yfinance`). Used only to build the trend gate (price vs its own
  200-day moving average, lagged one day). The index is used here because the
  live signal reads a freely available series; returns below are on the futures.
- **`overnight_path2.parquet` / `overnight_pct.parquet`** — derived from
  **NQ front-month futures 1-minute bars** (E-mini Nasdaq-100; MNQ is the
  1/10-size micro, same price, $2/point). Bars come from a retail futures feed
  (NinjaTrader historical export). For each night the front contract is the one
  with that day's highest volume; the values are aggregated over the
  16:00→09:00 ET hold. These are **derived per-night aggregates**, not a raw
  tick/quote feed.

### Columns

`overnight_path2.parquet`

| column | meaning | unit |
|---|---|---|
| `entry` | front-month price at 16:00 ET (entry) | index points |
| `hi` | highest print during the hold | index points |
| `lo` | lowest print during the hold | index points |
| `bars` | 1-minute bars in the window (median 945 — the 16:00→09:00 span minus the 17:00–18:00 ET maintenance halt) | count |

`overnight_pct.parquet`

| column | meaning | unit |
|---|---|---|
| `MNQ_ret` | overnight return, 16:00 close → 09:00 exit | fraction |
| `MNQ_close` | entry price — identical to `path2.entry` | index points |
| `MES_ret`, `MES_close` | same construction for the S&P 500 E-mini (MES) | — |

`MES_*` are carried for reference (an NQ-vs-ES comparison) and are **not used**
by `premium.py` or `account.py` — those read only the MNQ columns.

### How the path is used

- **Return** is `MNQ_ret` (close-to-close overnight P&L).
- The **+100pt take-profit** is decided from the path: it counts as filled
  whenever `hi/entry − 1` reaches the target during the night; otherwise the
  night is marked to the close. This is the only place an intra-night high
  enters the P&L.
- `lo` backs the drawdown / loss-limit reasoning (how far a night dipped before
  it recovered by the close).

Dollar figures convert returns at a fixed **$59,000 notional per contract**
($2/point × the current NQ level), so notional growth over 2014–2026 does not
distort the drawdown numbers.

## Run

    pip install -r requirements.txt
    python premium.py
    python account.py

## What `premium.py` prints

    overnight premium (16:00->09:00)
      all nights   +5.13 bp  t=3.56  win=57%
      gate on      +7.26 bp  t=5.23  win=59%
      gate off     -0.87 bp
      2c  mean $67.3  sd $533  sharpe 2.01  worst $-5785
      3c  mean $101.0 sd $799  sharpe 2.01  worst $-8677
      4c  mean $134.6 sd $1066 sharpe 2.01  worst $-11570

- `t` is the per-night t-stat, `mean / sd * sqrt(n)`.
- **Gate** = NDX above its own 200-day average (lagged one day) **and** past the
  2nd trading day of the month. The premium concentrates on gated nights
  (+7.26 bp, t=5.23); ungated nights are flat-to-negative (−0.87 bp).
- `2c/3c/4c` = contract count. Per-night P&L is repriced to a fixed $59,000
  notional per contract and capped by a +100pt (=$200/contract) take-profit
  whenever the night's high reaches it. Sharpe is annualized at sqrt(252).

## What `account.py` prints

Rolls the gated per-night P&L through a $10,000 account with a $1,500 trailing
drawdown and a 35%-of-peak giveback limit that arms once cumulative profit
passes $2,000, over rolling 504-night windows:

    2c: survived 7%   dd 49%  loss-limit 43%
    1c: survived 20%  ...

## Method note (the load-bearing assumption)

`account.py` judges each night as **one realized end-of-session step** — it does
not mark the drawdown intra-night. That matches a close / end-of-day liquidation
rule. Under an intra-night mark-to-market breach rule the survival numbers change
materially, because ~9% of nights touch below the trailing floor and recover by
the close. The distinction is the reason the strategy is viable only where the
breach check is end-of-day, not intra-session.

## Files

    premium.py   premium + per-night P&L / Sharpe
    account.py   account simulation (drawdown + loss-limit survival)
    data/        the three inputs above
