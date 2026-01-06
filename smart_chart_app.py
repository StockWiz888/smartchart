import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Smart Chart", page_icon="📊", layout="wide")
st.title("📊 Smart Chart — Buy / Sell Signal Assistant")

ticker = st.text_input("Enter Stock Symbol (e.g. AAPL, TSLA, MSFT)", "AAPL")

if st.button("Generate Signals"):
    try:
        ticker = ticker.strip().upper()
        st.info(f"Fetching {ticker} data …")

        # ---- Download price history ----
        data = yf.download(ticker, period="5y", interval="1d", progress=False)

        if data.empty:
            st.error(f"No data found for {ticker}.")
            st.stop()

        # ---- Force all columns to 1D Series ----
        for col in data.columns:
            data[col] = pd.Series(np.array(data[col]).reshape(-1), index=data.index)

        # ---- Manual indicator calculations (always 1D) ----
        delta = data["Close"].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        roll_up = pd.Series(gain).rolling(14).mean()
        roll_down = pd.Series(loss).rolling(14).mean()
        rs = roll_up / roll_down
        data["RSI"] = 100 - (100 / (1 + rs))

        data["MA20"] = data["Close"].rolling(window=20).mean()
        data["MA50"] = data["Close"].rolling(window=50).mean()

        exp1 = data["Close"].ewm(span=12, adjust=False).mean()
        exp2 = data["Close"].ewm(span=26, adjust=False).mean()
        data["MACD"] = exp1 - exp2
        data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

        data.dropna(inplace=True)

        # ---- Buy / Sell Logic ----
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

        # ---- Build Signal Table ----
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

        # ---- Display ----
        if not signal_df.empty:
            latest = signal_df.iloc[-1]
            st.metric(label=f"{latest['Type']} Signal",
                      value=f"${latest['Price']}",
                      delta=latest['Reason'])

        st.subheader("💹 Signal History")
        st.dataframe(signal_df.tail(25), use_container_width=True)

        # ---- Chart ----
        st.subheader("📈 Price Chart with Buy / Sell Points")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data.index, data["Close"], color="blue", lw=1.2, label="Close")
        ax.scatter(data.index, data["Buy"], color="green", marker="^", s=100, label="BUY")
        ax.scatter(data.index, data["Sell"], color="red", marker="v", s=100, label="SELL")
        ax.legend()
        ax.set_title(f"{ticker} — Buy / Sell Price Points")
        ax.set_ylabel("Price ($)")
        st.pyplot(fig)

        # ---- Summary ----
        st.subheader("📊 Signal Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Signals", len(signal_df))
        c2.metric("Buy Signals", len(signal_df[signal_df["Type"] == "BUY"]))
        c3.metric("Sell Signals", len(signal_df[signal_df["Type"] == "SELL"]))
        st.success("✅ Signal generation complete.")

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
