
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

MARKETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    "Gold": "GC=F",
    "US 500": "^GSPC",
    "US Tech 100": "^NDX",
}


def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram secrets are not configured.")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
    }).encode()

    request = urllib.request.Request(url, data=payload)
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("Telegram message failed.")


def analyse_market(name, ticker):
    df = yf.Ticker(ticker).history(
        period="5d", interval="5m", auto_adjust=True
    )

    if df.empty or len(df) < 60:
        return None

    close = df["Close"].dropna()
    if len(close) < 60:
        return None

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1/14, min_periods=14, adjust=False
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1/14, min_periods=14, adjust=False
    ).mean()

    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))

    macd = (
        close.ewm(span=12, adjust=False).mean()
        - close.ewm(span=26, adjust=False).mean()
    )
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    price = float(close.iloc[-1])
    current_rsi = float(rsi.iloc[-1])

    if pd.isna(current_rsi):
        return None

    bullish = (
        ema9.iloc[-1] > ema21.iloc[-1] > ema50.iloc[-1]
        and 52 <= current_rsi <= 68
        and macd.iloc[-1] > macd_signal.iloc[-1]
        and close.iloc[-1] > close.iloc[-2]
    )

    bearish = (
        ema9.iloc[-1] < ema21.iloc[-1] < ema50.iloc[-1]
        and 32 <= current_rsi <= 48
        and macd.iloc[-1] < macd_signal.iloc[-1]
        and close.iloc[-1] < close.iloc[-2]
    )

    if bullish:
        direction = "CALL"
    elif bearish:
        direction = "PUT"
    else:
        return None

    candle_time = close.index[-1]
    return {
        "name": name,
        "direction": direction,
        "price": price,
        "rsi": current_rsi,
        "candle_time": str(candle_time),
    }


def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Add Telegram secrets in GitHub Settings.")

    signals = []

    for name, ticker in MARKETS.items():
        try:
            result = analyse_market(name, ticker)
            if result:
                signals.append(result)
        except Exception as exc:
            print(f"Could not check {name}: {exc}")

    if not signals:
        print("No strong signal found. No Telegram message sent.")
        return

    lines = [
        "BFSS-STYLE MARKET ALERT",
        "Public Yahoo Finance data • 5-minute candles",
        "",
    ]

    for signal in signals:
        lines.extend([
            f"{signal['name']}: {signal['direction']}",
            f"Price: {signal['price']:.5f}",
            f"RSI: {signal['rsi']:.1f}",
            f"Candle: {signal['candle_time']}",
            "",
        ])

    lines.append(
        "Indicator output only — not a guaranteed prediction. "
        "Prices may differ from Quotex OTC."
    )

    send_telegram("\n".join(lines))
    print(f"Sent alert for {len(signals)} market(s).")


if __name__ == "__main__":
    main()
