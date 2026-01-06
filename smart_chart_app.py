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

        # ---- Fetch data ----
        stock = yf.Ticker(ticker)
        data = stock.history(period="5y", interval="1d")

        if data.empty:
            st.error(f"No data found for {ticker}.")
            st.stop()

        # ---- Indicators ----
        data["RSI"] = RSIIndicator(data["Close"], window=14).rsi().astype(float)
        data["MA20"] = SMAIndicator(data["Close"], window=20).sma_indicator().astype(float)
        data["MA50"] = SMAIndicator(data["Close"], window=50).sma_indicator().astype(float)
        macd = MACD(data["Close"])
        data["MACD"] = macd.macd().astype(float)
        data["MACD_Signal"] = macd.macd_signal().astype(float)
        data.dropna(inplace=True)

        # ---- Flatten to 1-D ----
        for col in ["RSI","MA20","MA50","MACD","MACD_Signal"]:
            data[col] = np.array(data[col]).reshape(-1)

        # ---- Signal logic ----
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
        signals=[]
        for i in range(len(data)):
            if not np.isnan(data["Buy"].iloc[i]):
                signals.append({"Date":data.index[i].strftime("%Y-%m-%d"),
                                "Type":"BUY",
                                "Price":round(data["Buy"].iloc[i],2),
                                "Reason":"RSI<30, MACD bullish, MA20>MA50"})
            elif not np.isnan(data["Sell"].iloc[i]):
                signals.append({"Date":data.index[i].strftime("%Y-%m-%d"),
                                "Type":"SELL",
                                "Price":round(data["Sell"].iloc[i],2),
                                "Reason":"RSI>70, MACD bearish, MA20<MA50"})
        signal_df=pd.DataFrame(signals)

        # ---- Display latest signal ----
        if not signal_df.empty:
            latest=signal_df.iloc[-1]
            st.metric(label=f"{latest['Type']} Signal",
                      value=f"${latest['Price']}",
                      delta=latest["Reason"])

        st.subheader("💹 Signal History")
        st.dataframe(signal_df.tail(25), use_container_width=True)

        # ---- Chart ----
        st.subheader("📈 Price Chart with Signals")
        fig, ax = plt.subplots(figsize=(12,6))
        ax.plot(data["Close"].values, color="blue", linewidth=1.1, label="Close")
        ax.scatter(data.index, data["Buy"], color="green", marker="^", s=100, label="BUY")
        ax.scatter(data.index, data["Sell"], color="red", marker="v", s=100, label="SELL")
        ax.legend()
        ax.set_title(f"{ticker} — Buy / Sell Price Points")
        ax.set_ylabel("Price ($)")
        st.pyplot(fig)

        # ---- Summary ----
        buys=len(signal_df[signal_df["Type"]=="BUY"])
        sells=len(signal_df[signal_df["Type"]=="SELL"])
        st.subheader("📊 Signal Summary")
        c1,c2,c3=st.columns(3)
        c1.metric("Total Signals", len(signal_df))
        c2.metric("Buy Signals", buys)
        c3.metric("Sell Signals", sells)
        st.success("✅ Signal generation complete.")

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
