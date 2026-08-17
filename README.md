# Overnight risk premium — Nasdaq-100 futures

Reproducible check of the overnight (16:00 → 09:00 ET) return in Nasdaq-100
index futures, plus a forward account simulation under a fixed trailing
drawdown and a percentage-giveback loss limit.

Everything below reproduces from a clean checkout — data is included.

## Data (`data/`)

| file | columns | span | rows |
|---|---|---|---|
| `ndx_cache.csv` | daily close | 2010-01-04 … 2026-08-17 | 4180 |
| `overnight_path2.parquet` | entry, hi, lo, bars | 2014-11-11 … 2026-07-31 | 2891 |
| `overnight_pct.parquet` | MNQ_ret, MNQ_close, MES_ret, MES_close | 2014-11-11 … 2026-08-03 | 2898 |

One row per night. `entry` is the 16:00 ET print; `hi`/`lo` are the extremes over
the hold to 09:00 ET the next morning; `*_ret` is the close-to-close overnight
return. Levels are continuous-front-month; the drawdown/notional figures use the
current MNQ contract ($2/point).

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
