import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import matplotlib.pyplot as plt

st.set_page_config(page_title="Smart Chart", page_icon="📊", layout="wide")
st.title("📊 Smart Chart — AI-Enhanced Stock Entry & Exit Signals")

ticker = st.text_input("Enter Stock Symbol (e.g. AAPL, TSLA, MSFT)", "AAPL")

if st.button("Generate Signal"):
    try:
        ticker = ticker.strip().upper()
        data = yf.download(ticker, start="2020-01-01", progress=False)

        if data.empty:
            st.error(f"❌ No price data returned for '{ticker}'. Try another symbol.")
            st.stop()

        # Indicators
        data["RSI"] = RSIIndicator(data["Close"], window=14).rsi()
        data["MA50"] = SMAIndicator(data["Close"], window=50).sma_indicator()
        data["MA200"] = SMAIndicator(data["Close"], window=200).sma_indicator()
        macd = MACD(data["Close"])
        data["MACD"] = macd.macd()
        data["MACD_Signal"] = macd.macd_signal()
        data.dropna(inplace=True)

        # Entry / Exit Logic
        data["Buy"] = np.where(
            (data["RSI"] < 30) & (data["MA50"] > data["MA200"]) & (data["MACD"] > data["MACD_Signal"]),
            data["Close"], np.nan)
        data["Sell"] = np.where(
            (data["RSI"] > 70) & (data["MA50"] < data["MA200"]) & (data["MACD"] < data["MACD_Signal"]),
            data["Close"], np.nan)

        # Generate trade log
        trade_log = []
        position = None
        for i in range(len(data)):
            if not np.isnan(data["Buy"].iloc[i]) and position is None:
                entry_price = data["Close"].iloc[i]
                entry_date = data.index[i]
                position = "long"
            elif not np.isnan(data["Sell"].iloc[i]) and position == "long":
                exit_price = data["Close"].iloc[i]
                exit_date = data.index[i]
                ret = (exit_price - entry_price) / entry_price * 100
                trade_log.append({
                    "Entry Date": entry_date.strftime("%Y-%m-%d"),
                    "Entry Price": round(entry_price, 2),
                    "Exit Date": exit_date.strftime("%Y-%m-%d"),
                    "Exit Price": round(exit_price, 2),
                    "Return (%)": round(ret, 2)
                })
                position = None

        trade_df = pd.DataFrame(trade_log)

        # --- Summary Stats ---
        if not trade_df.empty:
            total_trades = len(trade_df)
            avg_return = trade_df["Return (%)"].mean()
            win_rate = (trade_df["Return (%)"] > 0).mean() * 100
            st.subheader("📈 Performance Summary")
            st.write(f"**Total Trades:** {total_trades}")
            st.write(f"**Average Return:** {avg_return:.2f}%")
            st.write(f"**Win Rate:** {win_rate:.1f}%")

            st.subheader("💹 Trade History")
            st.dataframe(trade_df)

        # --- Chart ---
        st.subheader("📊 Price Chart with Entry/Exit Points")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data["Close"], label="Close Price", color="blue", linewidth=1.2)
        ax.scatter(data.index, data["Buy"], label="Buy (Entry)", marker="^", color="green", s=80)
        ax.scatter(data.index, data["Sell"], label="Sell (Exit)", marker="v", color="red", s=80)
        ax.legend()
        ax.set_title(f"{ticker} — Entry & Exit Signals")
        st.pyplot(fig)

        st.success("✅ Chart and trade analysis generated successfully.")

    except Exception as e:
        st.error(f"⚠️ Error occurred: {e}")
