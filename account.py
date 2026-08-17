import numpy as np, pandas as pd

def simulate(pnl, start=10000., dd=1500., safety=1600., act=2000., give=0.35, horizon=504):
    bal = pk = start
    cum = cum_pk = 0.0
    for x in pnl[:horizon]:
        bal += x; cum += x
        pk = max(pk, bal); cum_pk = max(cum_pk, cum)
        floor = min(pk - dd, start + safety - dd)      # EOD trail, locks once safety net hit
        if bal <= floor:
            return "dd_breach", cum
        if cum_pk >= act and cum < cum_pk * (1 - give): # 20% gain -> 35% giveback rule
            return "loss_limit", cum
    return "survived", cum

# quick sanity: survival rate under 2c vs 1c from current state
path = pd.read_parquet("data/overnight_path2.parquet")
ret  = pd.read_parquet("data/overnight_pct.parquet")["MNQ_ret"]
ndx  = pd.read_csv("data/ndx_cache.csv", index_col=0, parse_dates=True)["close"]
df = path.join(ret.rename("r"), how="inner").dropna()
above = (ndx/ndx.rolling(200).mean()-1).shift(1).reindex(df.index, method="ffill")
nth = pd.Series(df.index, index=df.index).groupby([df.index.year, df.index.month]).cumcount()+1
gate = ((above>0).fillna(False) & (nth.values>2)).values
r, mfe = df["r"].values, (df["hi"]/df["entry"]-1).values

def pnl_series(nc, tp):
    hit = mfe >= tp/(59000.*nc)
    g = np.where(hit, tp, r*59000.*nc) - 0.75*nc
    return np.where(gate, g, 0.0)

for nc, tp in ((2,400.),(1,200.)):
    outs=[]
    for s in range(0, len(r)-510, 5):
        o,_ = simulate(pnl_series(nc,tp)[s:s+504])
        outs.append(o)
    surv = np.mean([o=="survived" or isinstance(o,float) for o in outs])
    print(f"{nc}c: survived {np.mean([o=='survived' for o in outs])*100:.0f}%  "
          f"dd {np.mean([o=='dd_breach' for o in outs])*100:.0f}%  "
          f"loss-limit {np.mean([o=='loss_limit' for o in outs])*100:.0f}%")
