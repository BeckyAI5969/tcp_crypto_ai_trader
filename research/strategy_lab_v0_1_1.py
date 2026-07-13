r"""TCP Crypto AI Trader — Strategy Lab v0.1.1

Run from repository root:
    py -B research\strategy_lab_v0_1_1.py

Purpose: reproduce the original research strategy with one command and create
one complete report set for comparison with v0.1.0 and the historical benchmark.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports" / "strategy_lab" / "v0.1.1"
VERSION = "v0.1.1"
TIMEFRAME = "15m"
LOOKBACK_DAYS = 365
INITIAL_BALANCE = 5000.0
FIXED_NOTIONAL = 2500.0
TAKE_PROFIT_PCT = 0.04
STOP_LOSS_PCT = -0.02
FEE_RATE = 0.0
SLIPPAGE_RATE = 0.0
INTRABAR_PRIORITY = "STOP_FIRST"

DATASET_CANDIDATES = [
    DATA_DIR / "market_dataset.csv",
    DATA_DIR / "market_dataset.xlsx",
    DATA_DIR / "market_dataset.xls",
]

SYMBOL_RULES = {
    "BNBUSDT": {"min_score":60,"rsi_low":30,"rsi_high":55,"atr_mode":"sma20","volume_multiplier":1.15,"ema_confirm":True,"exit_mode":"ema20_exit"},
    "XRPUSDT": {"min_score":60,"rsi_low":30,"rsi_high":55,"atr_mode":"sma20","volume_multiplier":1.15,"ema_confirm":True,"exit_mode":"ema20_exit"},
    "ETHUSDT": {"min_score":60,"rsi_low":30,"rsi_high":60,"atr_mode":"sma20","volume_multiplier":1.10,"ema_confirm":True,"exit_mode":"ema20_exit"},
    "BTCUSDT": {"min_score":60,"rsi_low":30,"rsi_high":55,"atr_mode":"percentile40","volume_multiplier":1.15,"ema_confirm":True,"exit_mode":"ema20_exit"},
    "SOLUSDT": {"min_score":60,"rsi_low":30,"rsi_high":60,"atr_mode":"percentile40","volume_multiplier":1.20,"ema_confirm":True,"exit_mode":"ema20_exit"},
}

BENCHMARK = {
    "BNBUSDT": {"trades":66,"wins":54,"losses":12,"win_rate":81.82,"gross_profit":1214.82,"gross_loss":-652.47,"net_profit":562.35,"profit_factor":1.8619,"max_drawdown":-127.19,"expectancy":8.52},
    "XRPUSDT": {"trades":58,"wins":46,"losses":12,"win_rate":79.31,"gross_profit":1098.47,"gross_loss":-684.02,"net_profit":414.45,"profit_factor":1.6059,"max_drawdown":-260.06,"expectancy":7.15},
    "ETHUSDT": {"trades":121,"wins":92,"losses":29,"win_rate":76.03,"gross_profit":2595.75,"gross_loss":-1684.98,"net_profit":910.77,"profit_factor":1.5405,"max_drawdown":-365.91,"expectancy":7.53},
    "BTCUSDT": {"trades":62,"wins":50,"losses":12,"win_rate":80.65,"gross_profit":833.27,"gross_loss":-692.80,"net_profit":140.47,"profit_factor":1.2028,"max_drawdown":-256.26,"expectancy":2.27},
    "SOLUSDT": {"trades":146,"wins":100,"losses":46,"win_rate":68.49,"gross_profit":3022.23,"gross_loss":-2593.65,"net_profit":428.58,"profit_factor":1.1652,"max_drawdown":-433.81,"expectancy":2.94},
}

@dataclass
class Position:
    symbol: str
    entry_time: str
    entry_price: float
    quantity: float
    take_profit: float
    stop_loss: float
    ai_score: float
    entry_rsi: float
    entry_atr_pct: float
    entry_volume_ratio: float
    entry_ema_gap_pct: float
    entry_fee: float


def find_dataset() -> Path:
    for path in DATASET_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("market_dataset.csv/xlsx not found in data/")


def weighted_score(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0.0, index=df.index)
    score += (df["EMA20"] > df["EMA50"]).astype(float) * 35
    score += ((df["RSI14"] > 45) & (df["RSI14"] < 65)).astype(float) * 20
    score += (df["MACD"] > 0).astype(float) * 25
    score += 10
    score += (df["ATR14"] > 0).astype(float) * 10
    return score


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path) if path.suffix.lower()==".csv" else pd.read_excel(path)
    required = {"symbol","timeframe","open_time","open","high","low","close","volume","EMA20","EMA50","EMA200","RSI14","MACD","ATR14","VOLUME_MA20","atr_pct"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["timeframe"] = df["timeframe"].astype(str)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df[df["symbol"].isin(SYMBOL_RULES) & (df["timeframe"]==TIMEFRAME)].copy()
    groups=[]
    for symbol, group in df.groupby("symbol", sort=False):
        group = group.sort_values("open_time").drop_duplicates("open_time")
        cutoff = group["open_time"].max() - pd.Timedelta(days=LOOKBACK_DAYS)
        group = group[group["open_time"]>=cutoff].copy()
        group["ATR_MA20"] = group["ATR14"].rolling(20).mean()
        group["ATR_P40"] = group["ATR14"].rolling(200).quantile(.40)
        group["AI_SCORE"] = weighted_score(group)
        group["VOLUME_RATIO"] = group["volume"] / group["VOLUME_MA20"].replace(0,np.nan)
        group["EMA_GAP_PCT"] = (group["EMA20"]-group["EMA50"]) / group["close"].replace(0,np.nan) * 100
        groups.append(group)
    return pd.concat(groups, ignore_index=True)


def entry_allowed(group: pd.DataFrame, i: int, rule: dict[str,Any]) -> bool:
    row = group.iloc[i]
    if float(row["AI_SCORE"]) < rule["min_score"]: return False
    if not (rule["rsi_low"] <= float(row["RSI14"]) <= rule["rsi_high"]): return False
    if float(row["EMA50"]) <= float(row["EMA200"]): return False
    if rule["ema_confirm"]:
        if i < 1: return False
        prev = group.iloc[i-1]
        if not (float(row["close"]) > float(row["EMA20"]) and float(prev["close"]) > float(prev["EMA20"])): return False
    threshold = row["ATR_MA20"] if rule["atr_mode"]=="sma20" else row["ATR_P40"]
    if pd.isna(threshold) or float(row["ATR14"]) <= float(threshold): return False
    if float(row["volume"]) <= float(row["VOLUME_MA20"]) * rule["volume_multiplier"]: return False
    return True


def check_exit(row: pd.Series, pos: Position, exit_mode: str):
    sl_hit = float(row["low"]) <= pos.stop_loss
    tp_hit = float(row["high"]) >= pos.take_profit
    if sl_hit and tp_hit:
        return ("STOP_LOSS", pos.stop_loss) if INTRABAR_PRIORITY=="STOP_FIRST" else ("TAKE_PROFIT", pos.take_profit)
    if sl_hit: return "STOP_LOSS", pos.stop_loss
    if tp_hit: return "TAKE_PROFIT", pos.take_profit
    close = float(row["close"])
    if exit_mode=="ema20_exit" and close < float(row["EMA20"]) and close > pos.entry_price:
        return "EMA20_EXIT", close
    return None


def summarize(symbol: str, trades: list[dict[str,Any]], final_balance: float, max_dd: float) -> dict[str,Any]:
    wins=[t for t in trades if t["net_profit"]>0]
    losses=[t for t in trades if t["net_profit"]<0]
    gp=sum(t["net_profit"] for t in wins)
    gl=sum(t["net_profit"] for t in losses)
    net=final_balance-INITIAL_BALANCE
    pf=gp/abs(gl) if gl<0 else (float("inf") if gp>0 else 0.0)
    return {"strategy_version":VERSION,"symbol":symbol,"trades":len(trades),"wins":len(wins),"losses":len(losses),"win_rate":round(len(wins)/len(trades)*100,2) if trades else 0.0,"gross_profit":round(gp,2),"gross_loss":round(gl,2),"net_profit":round(net,2),"profit_factor":round(pf,4) if pf!=float("inf") else "Infinity","max_drawdown":round(max_dd,2),"expectancy":round(net/len(trades),2) if trades else 0.0,"initial_balance":INITIAL_BALANCE,"final_balance":round(final_balance,2),"return_pct":round(net/INITIAL_BALANCE*100,2)}


def replay_symbol(symbol: str, group: pd.DataFrame):
    rule=SYMBOL_RULES[symbol]
    group=group.reset_index(drop=True)
    balance=INITIAL_BALANCE; peak=INITIAL_BALANCE; max_dd=0.0; pos=None
    trades=[]; equity=[]
    for i in range(len(group)):
        row=group.iloc[i]; ts=row["open_time"].isoformat(); close=float(row["close"])
        if pos is not None:
            event=check_exit(row,pos,rule["exit_mode"])
            if event:
                reason,raw_exit=event
                exit_price=raw_exit*(1-SLIPPAGE_RATE)
                gross=(exit_price-pos.entry_price)*pos.quantity
                exit_fee=exit_price*pos.quantity*FEE_RATE
                net=gross-pos.entry_fee-exit_fee
                balance += net
                trades.append({"strategy_version":VERSION,"symbol":symbol,"entry_time":pos.entry_time,"exit_time":ts,"entry_price":round(pos.entry_price,8),"exit_price":round(exit_price,8),"quantity":round(pos.quantity,8),"notional":FIXED_NOTIONAL,"take_profit":round(pos.take_profit,8),"stop_loss":round(pos.stop_loss,8),"ai_score":pos.ai_score,"entry_rsi":pos.entry_rsi,"entry_atr_pct":pos.entry_atr_pct,"entry_volume_ratio":pos.entry_volume_ratio,"entry_ema_gap_pct":pos.entry_ema_gap_pct,"exit_reason":reason,"gross_profit":round(gross,8),"fees":round(pos.entry_fee+exit_fee,8),"net_profit":round(net,8),"result":"WIN" if net>0 else "LOSS","balance_after":round(balance,8)})
                pos=None
        if pos is None and entry_allowed(group,i,rule):
            entry=close*(1+SLIPPAGE_RATE); qty=FIXED_NOTIONAL/entry; fee=entry*qty*FEE_RATE
            pos=Position(symbol,ts,entry,qty,entry*(1+TAKE_PROFIT_PCT),entry*(1+STOP_LOSS_PCT),float(row["AI_SCORE"]),float(row["RSI14"]),float(row["atr_pct"]),float(row["VOLUME_RATIO"]),float(row["EMA_GAP_PCT"]),fee)
        unrealized=((close-pos.entry_price)*pos.quantity-pos.entry_fee) if pos else 0.0
        eq=balance+unrealized; peak=max(peak,eq); dd=eq-peak; max_dd=min(max_dd,dd)
        equity.append({"strategy_version":VERSION,"symbol":symbol,"open_time":ts,"balance":round(balance,8),"equity":round(eq,8),"drawdown":round(dd,8)})
    if pos is not None:
        row=group.iloc[-1]; exit_price=float(row["close"]); gross=(exit_price-pos.entry_price)*pos.quantity; exit_fee=0.0; net=gross-pos.entry_fee-exit_fee; balance+=net
        trades.append({"strategy_version":VERSION,"symbol":symbol,"entry_time":pos.entry_time,"exit_time":row["open_time"].isoformat(),"entry_price":round(pos.entry_price,8),"exit_price":round(exit_price,8),"quantity":round(pos.quantity,8),"notional":FIXED_NOTIONAL,"take_profit":round(pos.take_profit,8),"stop_loss":round(pos.stop_loss,8),"ai_score":pos.ai_score,"entry_rsi":pos.entry_rsi,"entry_atr_pct":pos.entry_atr_pct,"entry_volume_ratio":pos.entry_volume_ratio,"entry_ema_gap_pct":pos.entry_ema_gap_pct,"exit_reason":"END_OF_DATA","gross_profit":round(gross,8),"fees":round(pos.entry_fee+exit_fee,8),"net_profit":round(net,8),"result":"WIN" if net>0 else "LOSS","balance_after":round(balance,8)})
    return summarize(symbol,trades,balance,max_dd),trades,equity


def comparison(summary: pd.DataFrame) -> pd.DataFrame:
    rows=[]; metrics=("trades","wins","losses","win_rate","gross_profit","gross_loss","net_profit","profit_factor","max_drawdown","expectancy")
    for result in summary.to_dict("records"):
        symbol=result["symbol"]; old=BENCHMARK[symbol]; row={"strategy_version":VERSION,"symbol":symbol}
        for metric in metrics:
            row[f"baseline_{metric}"]=old[metric]; row[f"{VERSION}_{metric}"]=result[metric]
            row[f"difference_{metric}"]=round(result[metric]-old[metric],4) if isinstance(result[metric],(int,float)) else ""
        rows.append(row)
    return pd.DataFrame(rows)


def html_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False,escape=True,classes="data-table") if not df.empty else "<p>No data.</p>"


def strategy_score(summary: pd.DataFrame) -> float:
    pf=pd.to_numeric(summary["profit_factor"],errors="coerce").fillna(0).mean(); exp=summary["expectancy"].mean(); wr=summary["win_rate"].mean(); dd=summary["max_drawdown"].abs().mean()
    return round(float(np.clip(pf/2,0,1)*30 + np.clip((exp+10)/20,0,1)*25 + np.clip(wr/70,0,1)*20 + np.clip(1-dd/1000,0,1)*25),2)


def write_report(summary: pd.DataFrame,trades: pd.DataFrame,comp: pd.DataFrame,dataset: Path):
    total=len(trades); wins=int((trades["net_profit"]>0).sum()); wr=wins/total*100 if total else 0; net=trades["net_profit"].sum(); gp=trades.loc[trades["net_profit"]>0,"net_profit"].sum(); gl=trades.loc[trades["net_profit"]<0,"net_profit"].sum(); pf=gp/abs(gl) if gl<0 else float("inf"); score=strategy_score(summary)
    exit_analysis=trades.assign(is_win=trades["net_profit"]>0).groupby("exit_reason").agg(trades=("net_profit","size"),wins=("is_win","sum"),net_profit=("net_profit","sum"),average_trade=("net_profit","mean")).reset_index()
    cards=[("Version",VERSION),("Trades",f"{total:,}"),("Win Rate",f"{wr:.2f}%"),("Net Profit",f"{net:,.2f}"),("Profit Factor",f"{pf:.4f}"),("Strategy Score",f"{score:.2f}/100")]
    cards_html="".join(f"<div class='card'><div class='label'>{escape(k)}</div><div class='value'>{escape(v)}</div></div>" for k,v in cards)
    html=f"""<!doctype html><html><head><meta charset='utf-8'><title>Strategy Lab {VERSION}</title><style>body{{font-family:Segoe UI,Arial;background:#f4f6f8;color:#18212b;margin:0}}.container{{max-width:1400px;margin:auto;padding:28px}}.cards{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:20px 0}}.card{{background:white;border:1px solid #dce3e8;border-radius:10px;padding:16px}}.label{{font-size:12px;color:#66727f;text-transform:uppercase}}.value{{font-size:24px;font-weight:700}}h2{{margin-top:32px;border-bottom:2px solid #d9e0e6;padding-bottom:8px}}.data-table{{border-collapse:collapse;width:100%;background:white;font-size:12px;display:block;overflow:auto}}.data-table th,.data-table td{{border:1px solid #dce3e8;padding:7px 9px;white-space:nowrap}}.data-table th{{background:#243447;color:white}}.note{{background:#fff7ed;border-left:5px solid #ea580c;padding:14px;border-radius:6px}}</style></head><body><div class='container'><h1>TCP Crypto AI Trader — Strategy Lab {VERSION}</h1><p>Generated: {datetime.now(timezone.utc).isoformat()}<br>Dataset: {escape(str(dataset))}</p><div class='cards'>{cards_html}</div><div class='note'><b>Purpose:</b> benchmark parity. This version reproduces the original research-style strategy. It is not yet production-approved.</div><h2>Strategy Definition</h2><ul><li>Original weighted AI score</li><li>Symbol-specific RSI, ATR and volume filters</li><li>EMA confirmation</li><li>Fixed 4% take profit</li><li>Fixed -2% stop loss</li><li>Profitable EMA20 exit</li><li>Fixed notional 2,500 per trade</li><li>No fees/slippage for research parity</li></ul><h2>Performance Summary</h2>{html_table(summary)}<h2>Benchmark Comparison</h2>{html_table(comp)}<h2>Exit Analysis</h2>{html_table(exit_analysis)}<h2>Decision</h2><p>If v0.1.1 is close to the benchmark, the old strategy has been reproduced. If not, inspect entry timing and exit implementation before building v0.1.2.</p></div></body></html>"""
    (REPORT_DIR/"STRATEGY_REPORT_v0.1.1.html").write_text(html,encoding="utf-8")


def update_history(summary: pd.DataFrame):
    path=ROOT/"reports"/"strategy_lab"/"strategy_history.csv"; path.parent.mkdir(parents=True,exist_ok=True)
    row={"run_time_utc":datetime.now(timezone.utc).isoformat(),"strategy_version":VERSION,"total_trades":int(summary["trades"].sum()),"average_win_rate":round(summary["win_rate"].mean(),4),"total_net_profit":round(summary["net_profit"].sum(),4),"average_profit_factor":round(pd.to_numeric(summary["profit_factor"],errors="coerce").mean(),4),"worst_max_drawdown":round(summary["max_drawdown"].min(),4),"average_expectancy":round(summary["expectancy"].mean(),4),"strategy_score":strategy_score(summary)}
    hist=pd.read_csv(path) if path.exists() else pd.DataFrame(); pd.concat([hist,pd.DataFrame([row])],ignore_index=True).to_csv(path,index=False)


def main():
    print("="*72); print(f"TCP CRYPTO AI TRADER — STRATEGY LAB {VERSION}"); print("="*72)
    dataset=find_dataset(); print(f"Dataset: {dataset}"); data=load_data(dataset); REPORT_DIR.mkdir(parents=True,exist_ok=True)
    summaries=[]; all_trades=[]; all_equity=[]
    for symbol in SYMBOL_RULES:
        group=data[data["symbol"]==symbol].copy()
        if group.empty: print(f"{symbol}: no data — skipped"); continue
        print(f"{symbol}: replaying {len(group):,} candles...")
        summary,trades,equity=replay_symbol(symbol,group); summaries.append(summary); all_trades.extend(trades); all_equity.extend(equity)
        print(f"  trades={summary['trades']} | WR={summary['win_rate']}% | net={summary['net_profit']} | PF={summary['profit_factor']} | DD={summary['max_drawdown']}")
    summary_df=pd.DataFrame(summaries); trades_df=pd.DataFrame(all_trades); equity_df=pd.DataFrame(all_equity); comp_df=comparison(summary_df)
    summary_df.to_csv(REPORT_DIR/"backtest_summary.csv",index=False); trades_df.to_csv(REPORT_DIR/"trade_journal.csv",index=False); equity_df.to_csv(REPORT_DIR/"equity_curve.csv",index=False); comp_df.to_csv(REPORT_DIR/"benchmark_comparison.csv",index=False)
    manifest={"strategy_version":VERSION,"completed_at_utc":datetime.now(timezone.utc).isoformat(),"dataset":str(dataset),"timeframe":TIMEFRAME,"lookback_days":LOOKBACK_DAYS,"initial_balance_per_symbol":INITIAL_BALANCE,"fixed_notional_per_trade":FIXED_NOTIONAL,"take_profit_pct":TAKE_PROFIT_PCT,"stop_loss_pct":STOP_LOSS_PCT,"fee_rate":FEE_RATE,"slippage_rate":SLIPPAGE_RATE,"intrabar_priority":INTRABAR_PRIORITY,"purpose":"Reproduce original research benchmark","rules":SYMBOL_RULES,"future_columns_used_as_inputs":False}
    (REPORT_DIR/"strategy_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    write_report(summary_df,trades_df,comp_df,dataset); update_history(summary_df)
    print("\nSTRATEGY LAB v0.1.1 COMPLETED"); print(f"Reports: {REPORT_DIR}"); print(f"Open: {REPORT_DIR/'STRATEGY_REPORT_v0.1.1.html'}")

if __name__=="__main__": main()
