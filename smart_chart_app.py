import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
import matplotlib.pyplot as plt

# ---------- Streamlit layout ----------
st.set_page_config(page_title="Smart Chart", page_icon="📊", layout="wide")
st.title("📊 Smart Chart — Automatic Buy & Sell Signal Generator")

ticker = st.text_input("Enter Stock Symbol (e.g. AAPL, TSLA, MSFT)", "AAPL")

# ---------- When user clicks button ----------
if st.button("Generate Signals"):

    try:
        ticker = ticker.strip().upper()
        st.info(f"Fetching data for {ticker} ...")

        # ---------- Download market data ----------
        stock = yf.Ticker(ticker)
        data = stock.history(period="5y", interval="1d")

        if data.empty:
            st.error(f"❌ No data found for {ticker}.  Try another symbol.")
            st.stop()

        # ---------- Indicators ----------
        data["RSI"] = RSIIndicator(data["Close"], window=14).rsi()
        data["MA20"] = SMAIndicator(data["Close"], window=20).sma_indicator()
        data["MA50"] = SMAIndicator(data["Close"], window=50).sma_indicator()
        macd = MACD(data["Close"])
        data["MACD"] = macd.macd()
        data["MACD_Signal"] = macd.macd_signal()
        data.dropna(inplace=True)

        # ---------- Buy / Sell Logic ----------
        data["Buy_Price"] = np.where(
            (data["RSI"] < 30)
            & (data["MACD"] > data["MACD_Signal"])
            & (data["MA20"] > data["MA50"]),
            data["Close"],
            np.nan,
        )

        data["Sell_Price"] = np.where(
            (data["RSI"] > 70)
            & (data["MACD"] < data["MACD_Signal"])
            & (data["MA20"] < data["MA50"]),
            data["Close"],
            np.nan,
        )

        # ---------- Create Signal Table ----------
        signals = []
        for i in range(len(data)):
            if not np.isnan(data["Buy_Price"].iloc[i]):
                signals.append(
                    {
                        "Date": data.index[i].strftime("%Y-%m-%d"),
                        "Type": "BUY",
                        "Price": round(data["Buy_Price"].iloc[i], 2),
                        "Reason": "RSI<30, MACD bullish, MA20>MA50",
                    }
                )
            elif not np.isnan(data["Sell_Price"].iloc[i]):
                signals.append(
                    {
                        "Date": data.index[i].strftime("%Y-%m-%d"),
                        "Type": "SELL",
                        "Price": round(data["Sell_Price"].iloc[i], 2),
                        "Reason": "RSI>70, MACD bearish, MA20<MA50",
                    }
                )

        signal_df = pd.DataFrame(signals)

        # ---------- Show Latest Signal ----------
        if not signal_df.empty:
            latest = signal_df.iloc[-1]
            st.metric(
                label=f"Most Recent Signal: {latest['Type']}",
                value=f"${latest['Price']}",
                delta=latest["Reason"],
            )

        # ---------- Display Table ----------
        st.subheader("💹  Signal History")
        if not signal_df.empty:
            st.dataframe(signal_df.tail(25), use_container_width=True)
        else:
            st.write("No signals yet in the selected period.")

        # ---------- Plot Chart ----------
        st.subheader("📈  Price Chart with Entry / Exit Points")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data["Close"], color="blue", linewidth=1.1, label="Close")
        ax.scatter(
            data.index, data["Buy_Price"], color="green", marker="^", s=100, label="BUY"
        )
        ax.scatter(
            data.index, data["Sell_Price"], color="red", marker="v", s=100, label="SELL"
        )
        ax.legend()
        ax.set_title(f"{ticker} — Buy/Sell Price Points")
        ax.set_ylabel("Price ($)")
        st.pyplot(fig)

        # ---------- Performance Summary ----------
        buys = signal_df[signal_df["Type"] == "BUY"]
        sells = signal_df[signal_df["Type"] == "SELL"]
        total = len(signal_df)
        st.subheader("📊  Signal Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Signals", total)
        col2.metric("Buy Signals", len(buys))
        col3.metric("Sell Signals", len(sells))

        st.success("✅  Signal generation complete.")

    except Exception as e:
        st.error(f"⚠️  Error: {e}")
