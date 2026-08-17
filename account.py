"""계좌 시뮬 — $1,500 EOD 드로다운 + 누적 $2,000 후 최고의 35% 반납 손실한도. 504밤 롤링 생존율."""
import numpy as np, pandas as pd

def simulate(pnl,start=10000.,dd=1500.,safety=1600.,act=2000.,give=0.35,horizon=504):
    bal=pk=start; cum=cum_pk=0.
    for x in pnl[:horizon]:                          # 밤 하나 = 실현된 한 걸음
        bal+=x; cum+=x
        pk=max(pk,bal); cum_pk=max(cum_pk,cum)
        floor=min(pk-dd,start+safety-dd)             # EOD 트레일, 세이프티넷서 고정
        if bal<=floor: return "dd_breach"
        if cum_pk>=act and cum<cum_pk*(1-give): return "loss_limit"   # +20% 후 35% 반납
    return "survived"

path=pd.read_parquet("data/overnight_path2.parquet")
ret =pd.read_parquet("data/overnight_pct.parquet")["MNQ_ret"]
ndx =pd.read_csv("data/ndx_cache.csv",index_col=0,parse_dates=True)["close"]
df=path.join(ret.rename("r"),how="inner").dropna()
above=(ndx/ndx.rolling(200).mean()-1).shift(1).reindex(df.index,method="ffill")
nth=pd.Series(df.index,index=df.index).groupby([df.index.year,df.index.month]).cumcount()+1
gate=((above>0).fillna(False)&(nth.values>2)).values
r,mfe=df["r"].values,(df["hi"]/df["entry"]-1).values

def leg(nc,tp):
    hit=mfe>=tp/(59000.*nc)
    g=np.where(hit,tp,r*59000.*nc)-0.75*nc
    return np.where(gate,g,0.)

for nc,tp in ((2,400.),(1,200.)):
    o=[simulate(leg(nc,tp)[s:s+504]) for s in range(0,len(r)-510,5)]
    f=lambda k:np.mean([x==k for x in o])*100
    print("%dc: survived %.0f%%  dd %.0f%%  loss-limit %.0f%%"%(nc,f("survived"),f("dd_breach"),f("loss_limit")))
