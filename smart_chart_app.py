import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
import matplotlib.pyplot as plt

st.set_page_config(page_title="Smart Chart", page_icon="📊", layout="wide")
st.title("📊 Smart Chart — Buy / Sell Signal Assistant")

ticker = st.text_input("Enter Stock Symbol (e.g. AAPL, TSLA, MSFT)", "AAPL")

if st.button("Generate Signals"):
    try:
        ticker = ticker.strip().upper()
        st.info(f"Fetching {ticker} data …")

        # ---- Download price history ----
        stock = yf.Ticker(ticker)
        data = stock.history(period="5y", interval="1d")
        if data.empty:
            st.error(f"No data found for {ticker}.")
            st.stop()

        # ---- Indicators (force 1-D) ----
        data["RSI"] = pd.Series(RSIIndicator(data["Close"], 14).rsi().values.flatten(), index=data.index)
        data["MA20"] = pd.Series(SMAIndicator(data["Close"], 20).sma_indicator().values.flatten(), index=data.index)
        data["MA50"] = pd.Series(SMAIndicator(data["Close"], 50).sma_indicator().values.flatten(), index=data.index)

        macd = MACD(data["Close"])
        data["MACD"] = pd.Series(macd.macd().values.flatten(), index=data.index)
        data["MACD_Signal"] = pd.Series(macd.macd_signal().values.flatten(), index=data.index)
        data.dropna(inplace=True)

        # ---- Buy / Sell logic ----
        data["Buy"] = np.where(
            (data["RSI"] < 30)
            & (data["MACD"] > data["MACD_Signal"])
            & (data["MA20"] > data["MA50"]),
            data["Close"], np.nan)

        data["Sell"] = np.where(
            (data["RSI"] > 70)
            & (data["MACD"] < data["MACD_Signal"])
            & (data["MA20"] < data["MA50"]),
            data["Close"], np.nan)

        # ---- Build signal table ----
        signals = []
        for i in range(len(data)):
            if not np.isnan(data["Buy"].iloc[i]):
                signals.append({
                    "Date": data.index[i].strftime("%Y-%m-%d"),
                    "Type": "BUY",
                    "Price": round(data["Buy"].iloc[i], 2),
                    "Reason": "RSI<30, MACD bullish, MA20>MA50"
                })
            elif not np.isnan(data["Sell"].iloc[i]):
                signals.append({
                    "Date": data.index[i].strftime("%Y-%m-%d"),
                    "Type": "SELL",
                    "Price": round(data["Sell"].iloc[i], 2),
                    "Reason": "RSI>70, MACD bearish, MA20<MA50"
                })
        signal_df = pd.DataFrame(signals)

        # ---- Latest signal ----
        if not signal_df.empty:
            latest = signal_df.iloc[-1]
            st.metric(label=f"{latest['Type']} Signal",
                      value=f"${latest['Price']}",
                      delta=latest['Reason'])

        # ---- Table ----
        st.subheader("💹 Signal History")
        st.dataframe(signal_df.tail(25), use_container_width=True)

        # ---- Chart ----
        st.subheader("📈 Price Chart with Buy / Sell Points")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data.index, data["Close"].astype(float), color="blue", lw=1.1, label="Close")
        ax.scatter(data.index, data["Buy"], color="green", marker="^", s=100, label="BUY")
        ax.scatter(data.index, data["Sell"], color="red", marker="v", s=100, label="SELL")
        ax.legend()
        ax.set_title(f"{ticker} — Buy / Sell Price Points")
        ax.set_ylabel("Price ($)")
        st.pyplot(fig)

        # ---- Summary ----
        st.subheader("📊 Signal Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Signals", len(signal_df))
        col2.metric("Buy Signals", len(signal_df[signal_df["Type"] == "BUY"]))
        col3.metric("Sell Signals", len(signal_df[signal_df["Type"] == "SELL"]))
        st.success("✅ Signal generation complete.")

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
