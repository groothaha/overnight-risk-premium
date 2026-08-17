"""밤 프리미엄(16:00→09:00)·게이트 효과·계약수별 밤손익."""
import numpy as np, pandas as pd

FEE,NOTIONAL=0.75,59000.        # 왕복수수료/계약 · 계약당 노셔널(현재)

ndx =pd.read_csv("data/ndx_cache.csv",index_col=0,parse_dates=True)["close"]
path=pd.read_parquet("data/overnight_path2.parquet")
ret =pd.read_parquet("data/overnight_pct.parquet")["MNQ_ret"]

df=path.join(ret.rename("r"),how="inner").dropna()
above=(ndx/ndx.rolling(200).mean()-1).shift(1).reindex(df.index,method="ffill")
nth=pd.Series(df.index,index=df.index).groupby([df.index.year,df.index.month]).cumcount()+1
gate=((above>0).fillna(False)&(nth.values>2)).values
r=df["r"].values; mfe=(df["hi"]/df["entry"]-1).values

def stat(x):
    m,s=x.mean(),x.std(ddof=1)
    return m*1e4, m/s*np.sqrt(len(x)), (x>0).mean()*100

print("overnight premium (16:00->09:00)")
print("  all nights   %+.2f bp  t=%.2f  win=%.0f%%"%stat(r))
print("  gate on      %+.2f bp  t=%.2f  win=%.0f%%"%stat(r[gate]))
print("  gate off     %+.2f bp"%(r[~gate].mean()*1e4,))

def pnl(nc,tp):
    hit=mfe>=tp/(NOTIONAL*nc)                    # 밤중 익절선 터치면 tp, 아니면 종가마크
    g=np.where(hit,tp,r*NOTIONAL*nc)-FEE*nc
    return np.where(gate,g,0.)

for nc in (2,3,4):
    v=pnl(nc,200.*nc)[gate]
    print("  %dc  mean $%.1f  sd $%.0f  sharpe %.2f  worst $%.0f"
          %(nc,v.mean(),v.std(ddof=1),v.mean()/v.std(ddof=1)*np.sqrt(252),v.min()))
