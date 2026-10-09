import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="BFSS Web Predictor", page_icon="📊")
st.title("🔷 BFSS STYLE — NEXT PREDICTED SIGNAL")
st.caption("Browser signal viewer • public market data • signal-only")

MARKETS={"EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X","USD/CHF":"CHF=X","AUD/USD":"AUDUSD=X","USD/CAD":"CAD=X","XAU/USD":"GC=F","BTC/USD":"BTC-USD","ETH/USD":"ETH-USD","US 500":"^GSPC","US Tech 100":"^NDX"}

def analyze(name,ticker,interval):
    df=yf.download(ticker,period="5d",interval=interval,progress=False,auto_adjust=False)
    if df is None or len(df)<60:return None
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    c=df["Close"].dropna().astype(float)
    e9=c.ewm(span=9,adjust=False).mean();e21=c.ewm(span=21,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean()
    d=c.diff();g=d.clip(lower=0).rolling(14).mean();l=(-d.clip(upper=0)).rolling(14).mean()
    rsi=100-(100/(1+g/l.replace(0,np.nan)))
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean();sig=macd.ewm(span=9,adjust=False).mean()
    mom=float(c.pct_change(3).iloc[-1]*100);score=0
    score+=1 if e9.iloc[-1]>e21.iloc[-1] else -1
    score+=1 if e21.iloc[-1]>e50.iloc[-1] else -1
    score+=1 if macd.iloc[-1]>sig.iloc[-1] else -1
    rv=float(rsi.iloc[-1])
    if 52<=rv<=70:score+=1
    elif 30<=rv<=48:score-=1
    if mom>.03:score+=1
    elif mom<-.03:score-=1
    direction="CALL" if score>=3 else "PUT" if score<=-3 else "WAIT"
    conf=min(95,50+abs(score)*8+min(15,abs(mom)*2))
    return name,direction,score,rv,mom,round(conf),df

tf=st.selectbox("Timeframe",["1m","5m","15m","30m"],index=1)
expiry=st.selectbox("Expiry",["1m","2m","5m","10m"],index=1)
if st.button("🎯 PREDICT NEXT SIGNAL"):
    results=[]
    for n,t in MARKETS.items():
        try:
            r=analyze(n,t,tf)
            if r and r[1]!="WAIT":results.append(r)
        except Exception:pass
    if results:
        r=max(results,key=lambda x:x[5]+abs(x[2])*5)
        name,direction,score,rv,mom,conf,df=r
        st.subheader("🎯 NEXT PREDICTED SIGNAL")
        st.write("**Asset:**",name)
        st.success("🟢 CALL" if direction=="CALL" else "🔴 PUT")
        st.write(f"**Expiry:** {expiry}  |  **Confidence:** {conf}%  |  **Score:** {score:+d}/5")
        st.write(f"**RSI:** {rv:.2f}  |  **Momentum:** {mom:.2f}%")
        st.line_chart(df[["Close"]].tail(100))
        st.warning("Probability-based analysis only. No guaranteed profit and no automatic trades.")
    else: st.info("No strong setup found. Try again later.")
else: st.info("Click PREDICT NEXT SIGNAL to scan the markets.")

st.caption("Public market data only; Quotex OTC prices may differ.")
