import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import matplotlib.pyplot as plt

# Streamlit Page Setup
st.set_page_config(page_title="Smart Chart 2.0", page_icon="📊", layout="wide")
st.title("📊 Smart Chart 2.0 — Buy/Sell Signal Assistant")

ticker = st.text_input("Enter Stock Symbol (e.g. AAPL, TSLA, MSFT)", "AAPL")

if st.button("Generate Signals"):
    try:
        ticker = ticker.strip().upper()
        st.info(f"Fetching {ticker} data...")
        data = yf.download(ticker, start="2020-01-01", progress=False)

        if data.empty:
            st.error(f"❌ No data found for {ticker}. Try another symbol.")
            st.stop()

        # --- Technical Indicators ---
        data["RSI"] = RSIIndicator(data["Close"], window=14).rsi()
        data["MA20"] = SMAIndicator(data["Close"], window=20).sma_indicator()
        data["MA50"] = SMAIndicator(data["Close"], window=50).sma_indicator()
        data["MA200"] = SMAIndicator(data["Close"], window=200).sma_indicator()
        macd = MACD(data["Close"])
        data["MACD"] = macd.macd()
        data["MACD_Signal"] = macd.macd_signal()
        data.dropna(inplace=True)

        # --- Buy and Sell Conditions ---
        data["Buy_Signal"] = np.where(
            (data["RSI"] < 30)
            & (data["MACD"] > data["MACD_Signal"])
            & (data["MA20"] > data["MA50"]),
            data["Close"], np.nan)

        data["Sell_Signal"] = np.where(
            (data["RSI"] > 70)
            & (data["MACD"] < data["MACD_Signal"])
            & (data["MA20"] < data["MA50"]),
            data["Close"], np.nan)

        # --- Build Signal Table ---
        signals = []
        for i in range(len(data)):
            if not np.isnan(data["Buy_Signal"].iloc[i]):
                signals.append({
                    "Date": data.index[i].strftime("%Y-%m-%d"),
                    "Type": "BUY",
                    "Price": round(data["Buy_Signal"].iloc[i], 2),
                    "Reason": "RSI<30, MACD Bullish, MA20>MA50"
                })
            elif not np.isnan(data["Sell_Signal"].iloc[i]):
                signals.append({
                    "Date": data.index[i].strftime("%Y-%m-%d"),
                    "Type": "SELL",
                    "Price": round(data["Sell_Signal"].iloc[i], 2),
                    "Reason": "RSI>70, MACD Bearish, MA20<MA50"
                })

        signal_df = pd.DataFrame(signals)

        # --- Show Signal Summary ---
        if not signal_df.empty:
            st.subheader("📈 Latest Signal")
            latest = signal_df.iloc[-1]
            st.metric(
                label=f"{latest['Type']} Signal",
                value=f"${latest['Price']}",
                delta=latest['Reason']
            )

            st.subheader("💹 Signal History")
            st.dataframe(signal_df.tail(20), use_container_width=True)
        else:
            st.warning("⚠️ No recent BUY or SELL signals were detected.")

        # --- Plot Chart ---
        st.subheader("📊 Price Chart with Buy/Sell Points")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data["Close"], label="Close Price", color="blue", linewidth=1.2)
        ax.scatter(data.index, data["Buy_Signal"], color="green", marker="^", s=100, label="BUY Signal")
        ax.scatter(data.index, data["Sell_Signal"], color="red", marker="v", s=100, label="SELL Signal")
        ax.legend()
        ax.set_title(f"{ticker} — Buy/Sell Price Points")
        st.pyplot(fig)

        # --- Summary Stats ---
        if not signal_df.empty:
            total_signals = len(signal_df)
            buy_signals = len(signal_df[signal_df["Type"] == "BUY"])
            sell_signals = len(signal_df[signal_df["Type"] == "SELL"])
            st.subheader("📊 Signal Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Signals", total_signals)
            col2.metric("Buy Signals", buy_signals)
            col3.metric("Sell Signals", sell_signals)

        st.success("✅ Signal generation complete.")

    except Exception as e:
        st.error(f"⚠️ Error occurred: {e}")
