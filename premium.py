import numpy as np, pandas as pd

TICK, PT_VAL = 0.25, 2.0          # MNQ: 0.25pt tick, $2/pt
FEE = 0.75                        # round-trip per contract
NOTIONAL = 59000.0                # current per-contract notional

px  = pd.read_parquet("data/ndx_cache.csv".replace(".csv",".parquet")) if False else None
ndx = pd.read_csv("data/ndx_cache.csv", index_col=0, parse_dates=True)["close"]
path = pd.read_parquet("data/overnight_path2.parquet")   # entry, hi, lo per night
ret  = pd.read_parquet("data/overnight_pct.parquet")["MNQ_ret"]

df = path.join(ret.rename("r"), how="inner").dropna()
ma200 = ndx.rolling(200).mean()
above = (ndx / ma200 - 1).shift(1).reindex(df.index, method="ffill")
nth = pd.Series(df.index, index=df.index).groupby([df.index.year, df.index.month]).cumcount() + 1
gate = (above > 0).fillna(False) & (nth.values > 2)

r = df["r"].values
mfe = (df["hi"] / df["entry"] - 1).values

def stat(x):
    m, s = x.mean(), x.std(ddof=1)
    return m*1e4, m/s*np.sqrt(len(x)), (x > 0).mean()*100

# 1. premium
print("overnight premium (16:00->09:00)")
print("  all nights   %+.2f bp  t=%.2f  win=%.0f%%" % stat(r))
print("  gate on      %+.2f bp  t=%.2f  win=%.0f%%" % stat(r[gate.values]))
print("  gate off     %+.2f bp" % (r[~gate.values].mean()*1e4,))

# 2. per-night P&L, notional-repriced, with take-profit
def night_pnl(nc, tp_dollar):
    tp_ret = tp_dollar / (NOTIONAL * nc)
    hit = mfe >= tp_ret
    gross = np.where(hit, tp_dollar, r * NOTIONAL * nc)
    return np.where(gate.values, gross - FEE*nc, 0.0)

for nc in (2, 3, 4):
    v = night_pnl(nc, 200.0*nc)
    v = v[gate.values]
    print("  %dc  mean $%.1f  sd $%.0f  sharpe %.2f  worst $%.0f"
          % (nc, v.mean(), v.std(ddof=1), v.mean()/v.std(ddof=1)*np.sqrt(252), v.min()))
