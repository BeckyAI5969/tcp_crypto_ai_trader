
from pathlib import Path
from datetime import datetime, timezone
import csv, json, shutil

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"strategy_lab"

DIRS=["dashboard","strategies","history","analyzers","knowledge","experiments","templates","manifest"]

REGISTRY=[
{"version":"research_original","display_name":"Research Original","edition":"Research Benchmark","parent":"","status":"BENCHMARK","goal":"Original optimized research benchmark",
"manual":{"profit_factor":1.4753,"win_rate":77.26,"max_drawdown":-288.65,"net_profit":491.32,"score":95.0},
"dna":{"entry":"Optimized weighted signal with symbol-specific filters","exit":"Fixed TP/SL plus EMA20 exit","risk":"Research fixed sizing","position_size":"Fixed notional","ai":"Weighted score","indicators":"EMA, RSI, MACD, ATR, Volume","filters":"Symbol-specific filters"},
"changes":["Original benchmark"],"lessons":["Strong in-sample result","Walk-forward robustness still required"]},
{"version":"v0.1.0","display_name":"v0.1.0","edition":"Production Baseline","parent":"research_original","status":"ARCHIVED","goal":"Production-style pipeline baseline",
"summary":"reports/backtest_v0.1.0/backtest_summary.csv",
"dna":{"entry":"Weighted signal plus optimized filters","exit":"ATR SL/TP plus EMA20 exit","risk":"Dynamic","position_size":"Dynamic risk sizing","ai":"Pipeline approval score","indicators":"EMA, RSI, MACD, ATR, Volume","filters":"Production filters"},
"changes":["Dynamic leverage","Dynamic sizing","ATR exit"],"lessons":["AI score constant","Stop losses dominated","Performance below benchmark"]},
{"version":"v0.1.1","display_name":"v0.1.1","edition":"Research Recovery Edition","parent":"v0.1.0","status":"CANDIDATE","goal":"Recover original research performance",
"summary":"reports/strategy_lab/v0.1.1/backtest_summary.csv",
"dna":{"entry":"Original weighted score and filters","exit":"4% TP, -2% SL, EMA20 profit exit","risk":"Research parity","position_size":"Fixed notional 2,500","ai":"Original weighted score","indicators":"EMA, RSI, MACD, ATR, Volume","filters":"Original research filters"},
"changes":["Restored research exits","Restored fixed sizing","No fees/slippage for parity"],"lessons":["Positive edge recovered","Close to benchmark","SOL/BTC weaker"]},
{"version":"v0.1.2","display_name":"v0.1.2","edition":"Market Regime Edition","parent":"v0.1.1","status":"PLANNED","goal":"Test market-regime gate only",
"manual":{},"dna":{"entry":"v0.1.1 plus regime gate","exit":"Same as v0.1.1","risk":"Same as v0.1.1","position_size":"Same as v0.1.1","ai":"Same as v0.1.1","indicators":"Add Regime","filters":"Market regime only"},
"changes":["Planned controlled change: market regime filter"],"lessons":[]}
]

def read_metrics(rel):
    p=ROOT/rel
    if not p.exists(): return {}
    rows=list(csv.DictReader(p.open(encoding="utf-8-sig")))
    def vals(c):
        out=[]
        for r in rows:
            try: out.append(float(r[c]))
            except: pass
        return out
    trades=vals("trades"); wins=vals("wins"); pf=vals("profit_factor"); dd=vals("max_drawdown"); net=vals("net_profit"); ex=vals("expectancy")
    m={}
    if trades:m["trades"]=sum(trades)
    if wins and trades and sum(trades):m["win_rate"]=sum(wins)/sum(trades)*100
    if pf:m["profit_factor"]=sum(pf)/len(pf)
    if dd:m["max_drawdown"]=min(dd)
    if net:m["net_profit"]=sum(net)
    if ex:m["expectancy"]=sum(ex)/len(ex)
    return m

def score(m):
    if not m:return 0
    pf=max(0,m.get("profit_factor",0)); wr=max(0,m.get("win_rate",0)); dd=abs(m.get("max_drawdown",0)); ex=m.get("expectancy",0); net=m.get("net_profit",0)
    return round(min(pf/2,1)*30+min(wr/80,1)*20+max(0,1-dd/3000)*20+max(0,min((ex+10)/20,1))*15+max(0,min((net+7000)/10000,1))*15,2)

def main():
    print("="*72); print("TCP STRATEGY LAB PLATFORM v1.0 — SPRINT 27"); print("="*72)
    for d in DIRS:(LAB/d).mkdir(parents=True,exist_ok=True)
    manifests=[]
    for s in REGISTRY:
        vdir=LAB/"strategies"/s["version"]
        for sub in ["reports","analysis","notes"]: (vdir/sub).mkdir(parents=True,exist_ok=True)
        m=dict(s.get("manual",{}))
        if s.get("summary"): m=read_metrics(s["summary"]) or m
        m["score"]=m.get("score",score(m))
        man={"version":s["version"],"display_name":s["display_name"],"edition":s["edition"],"parent":s["parent"],"status":s["status"],"goal":s["goal"],"created_at_utc":datetime.now(timezone.utc).isoformat(),"metrics":m,"strategy_dna":s["dna"],"changes":s["changes"],"lessons":s["lessons"]}
        (vdir/"manifest.json").write_text(json.dumps(man,indent=2,ensure_ascii=False),encoding="utf-8")
        manifests.append(man)
        print("Registered:",s["display_name"])

    hp=LAB/"history"/"strategy_history.csv"
    with hp.open("w",encoding="utf-8-sig",newline="") as f:
        cols=["version","display_name","edition","parent","status","goal","profit_factor","win_rate","max_drawdown","net_profit","expectancy","trades","score"]
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for m in manifests:
            mt=m["metrics"]; w.writerow({**{k:m.get(k,"") for k in cols},**{k:mt.get(k,"") for k in ["profit_factor","win_rate","max_drawdown","net_profit","expectancy","trades","score"]}})
    (LAB/"history"/"version_tree.json").write_text(json.dumps({"nodes":[{"version":m["version"],"parent":m["parent"],"goal":m["goal"],"status":m["status"]} for m in manifests]},indent=2),encoding="utf-8")

    kb={"winning_patterns.json":{"patterns":[]},"losing_patterns.json":{"patterns":[]},"indicator_memory.json":{"indicators":{}},"ai_learning.json":{"lessons":[{"source":"v0.1.0","lesson":"Constant AI score cannot rank trades"},{"source":"v0.1.1","lesson":"Research exits and fixed sizing recovered edge"}]}}
    for n,payload in kb.items():
        p=LAB/"knowledge"/n
        if not p.exists(): p.write_text(json.dumps(payload,indent=2),encoding="utf-8")

    import sys
    sys.path.insert(0,str(LAB/"dashboard"))
    from strategy_dashboard import generate_dashboard
    out=generate_dashboard(ROOT)
    print("\nSPRINT 27 COMPLETED")
    print("Open dashboard:",out)

if __name__=="__main__": main()
