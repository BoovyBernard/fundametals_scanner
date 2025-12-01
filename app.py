import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import datetime
import html2text

# -------------------------------
# AUTO REFRESH (optional toggle)
# -------------------------------
if "auto" not in st.session_state:
    st.session_state.auto = False

def auto_refresh():
    if st.session_state.auto:
        st_autorefresh(interval=60_000, limit=None)

auto_refresh()

# -------------------------------
# UI
# -------------------------------
st.title("📊 AI Market Scanner — Stocks, ETFs, Sectors, Indices")

st.write("A Streamlit Cloud–optimized scanner that analyzes news, fundamentals, trends & creates a Bullish/Bearish rating.")

scan_type = st.selectbox("Select type:", ["Single Asset", "Sector Scan", "ETF Scan"])

# -------------------------------
# DEFAULT ETF & SECTOR LISTS
# -------------------------------
etf_list = ["SPY", "QQQ", "DIA", "IWM", "VWO", "EEM", "XLF", "XLE", "XLK", "XLV", "XLY", "XLP", "XLB", "IYR"]
sector_list = ["XLK", "XLF", "XLE", "XLY", "XLP", "XLI", "XLV", "XLB", "XLU"]

# -------------------------------
# Ticker Input
# -------------------------------
if scan_type == "Single Asset":
    tickers = [st.text_input("Enter ticker:", "AAPL").upper()]
elif scan_type == "Sector Scan":
    tickers = sector_list
    st.info("Scanning major US sectors…")
else:
    tickers = etf_list
    st.info("Scanning top ETFs…")

# -------------------------------
# Sliders - Weighting
# -------------------------------
st.subheader("⚙️ Scoring Weight Adjustments")
w_news = st.slider("News Sentiment Weight", 0, 50, 20)
w_fund = st.slider("Fundamental Weight", 0, 50, 20)
w_trend = st.slider("Trend Weight", 0, 50, 20)

# -------------------------------
# SCRAPE NEWS (Lightweight)
# -------------------------------
def fetch_news(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}?p={ticker}"
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all("h3", limit=5)
        return [a.text for a in articles]
    except:
        return []

# -------------------------------
# LIGHTWEIGHT SENTIMENT ANALYSIS
# Rule-based sentiment (cloud safe)
# -------------------------------
positive_words = ["beats", "soars", "growth", "jump", "rises", "strong", "profit"]
negative_words = ["falls", "misses", "drop", "weak", "loss", "cuts", "bad"]

def sentiment_score(text):
    text = text.lower()
    pos = sum(word in text for word in positive_words)
    neg = sum(word in text for word in negative_words)
    return pos - neg

# -------------------------------
# FUNDAMENTAL SCORE
# -------------------------------
def fundamental_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        fin = stock.financials
        if fin.empty:
            return 0, "No financials"
        rev = fin.loc["Total Revenue"].iloc[:2]
        ni = fin.loc["Net Income"].iloc[:2]

        score = 0
        reason = []

        if rev.iloc[0] > rev.iloc[1]:
            score += 10
            reason.append("Revenue growing")
        else:
            score -= 10
            reason.append("Revenue declining")

        if ni.iloc[0] > ni.iloc[1]:
            score += 10
            reason.append("Net income improving")
        else:
            score -= 10
            reason.append("Net income declining")

        return score, ", ".join(reason)
    except:
        return 0, "Financial analysis error"

# -------------------------------
# TREND SCORE
# -------------------------------
def trend_score(ticker):
    try:
        data = yf.download(ticker, period="3mo")
        if data.empty:
            return 0, "No data"

        price = data["Close"].iloc[-1]
        ma20 = data["Close"].rolling(20).mean().iloc[-1]

        if price > ma20:
            return 10, "Uptrend"
        else:
            return -10, "Downtrend"
    except:
        return 0, "Trend error"

# -------------------------------
# FINAL CLASSIFICATION
# -------------------------------
def classify(score):
    if score >= 60: return "🔥 STRONG BULLISH"
    if score >= 40: return "🟢 BULLISH"
    if score >= 25: return "🟡 NEUTRAL"
    if score >= 10: return "🔻 BEARISH"
    return "🛑 STRONG BEARISH"

# -------------------------------
# REPORT GENERATOR
# -------------------------------
def generate_report(results):
    html = "<h1>Market Scanner Report</h1>"
    for r in results:
        html += f"<h3>{r['ticker']}</h3>"
        html += f"<p>Score: {r['final_score']} — {r['signal']}</p>"
        html += f"<p>News Score: {r['news']}</p>"
        html += f"<p>Fundamentals: {r['fund']} ({r['fund_reason']})</p>"
        html += f"<p>Trend: {r['trend']} ({r['trend_reason']})</p>"
        html += "<hr>"
    return html

# -------------------------------
# RUN SCANNER
# -------------------------------
st.subheader("📡 Scan Results")

results = []

for ticker in tickers:
    # News
    news = fetch_news(ticker)
    news_score = sum(sentiment_score(n) for n in news) * 5

    # Fundamentals
    f_score, f_reason = fundamental_score(ticker)

    # Trend
    t_score, t_reason = trend_score(ticker)

    final = (
        news_score * (w_news / 50)
        + f_score * (w_fund / 50)
        + t_score * (w_trend / 50)
    )

    results.append({
        "ticker": ticker,
        "news": round(news_score, 2),
        "fund": round(f_score, 2),
        "fund_reason": f_reason,
        "trend": round(t_score, 2),
        "trend_reason": t_reason,
        "final_score": round(final, 2),
        "signal": classify(final)
    })

df = pd.DataFrame(results)
st.dataframe(df)

# -------------------------------
# Download Web Report (HTML)
# -------------------------------
report_html = generate_report(results)

st.download_button(
    label="📄 Download HTML Report",
    data=report_html,
    file_name="market_report.html",
    mime="text/html"
)

# -------------------------------
# Auto Refresh Toggle
# -------------------------------
st.checkbox("Enable Auto-Scan Every 60s", key="auto")
