# app.py — Market Pulse Lite (datos macro desde Yahoo Finance)

import datetime as dt
import base64
import tempfile

import pandas as pd
import streamlit as st
import feedparser
from textblob import TextBlob
import yfinance as yf
import weasyprint

# ---------------------------------------
# Tickers Yahoo Finance → etiquetas
# ---------------------------------------
SERIES = {
    "^TNX": "10Y Yield",   # US 10-year Treasury yield
    "^FVX": "5Y Yield",    # US 5-year Treasury yield
    "^IRX": "3M Yield"     # US 3-month T-bill yield
}

@st.cache_data
def get_macro():
    dfs = []
    for ticker, label in SERIES.items():
        # Descarga 3 años diarios (precio de cierre)
        hist = yf.download(ticker, period="3y", progress=False)
        if hist.empty:
            st.warning(f"⚠️ Ticker {ticker} no disponible.")
            continue
        s = hist["Close"].rename(label)
        dfs.append(s)
    return pd.concat(dfs, axis=1) if dfs else pd.DataFrame()

@st.cache_data
def get_sentiment():
    RSS = "http://feeds.reuters.com/reuters/businessNews"
    feed = feedparser.parse(RSS)
    rows = []
    # Tomamos sólo los primeros 50 titulares
    for entry in feed.entries[:50]:
        # Fecha: published_parsed o UTC actual
        if hasattr(entry, "published_parsed"):
            ts = dt.datetime(*entry.published_parsed[:6])
        else:
            ts = dt.datetime.utcnow()
        score = TextBlob(entry.title).sentiment.polarity
        rows.append({"time": ts, "title": entry.title, "score": score})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["hour"] = df["time"].dt.floor("H")
    return df

def to_pdf(latest_series: pd.Series):
    html = f"""
    <h1>Macro Snapshot</h1>
    <p>Fecha: {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC</p>
    {latest_series.to_frame("Value").to_html(border=0)}
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    weasyprint.HTML(string=html).write_pdf(tmp.name)
    return tmp.name

def main():
    st.set_page_config(page_title="Market Pulse Lite", layout="wide")
    st.title("📊 Market Pulse Lite")
    st.caption(f"Actualizado: {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC")

    # — 1. Macro —
    macro = get_macro()
    if macro.empty:
        st.error("No se pudo cargar los datos macro.")
    else:
        st.subheader("Indicadores macro (US Treasuries, últimos 3 años)")
        st.line_chart(macro)

        latest = macro.tail(1).T
        latest.columns = ["Value"]
        st.subheader("Último dato disponible")
        st.table(latest)

    # — 2. Sentiment —
    sentiment = get_sentiment()
    if sentiment.empty:
        st.warning("No hay datos de sentimiento disponibles.")
    else:
        sent_hourly = sentiment.groupby("hour")["score"].mean().to_frame()
        st.subheader("Sentimiento Reuters (últimas 24 h)")
        st.line_chart(sent_hourly.tail(24))

    # — 3. PDF —
    if not macro.empty and st.button("📄 Descargar PDF"):
        pdf_path = to_pdf(macro.tail(1).iloc[0])
        with open(pdf_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        link = (
            f'<a href="data:application/pdf;base64,{b64}" '
            'download="macro_snapshot.pdf">👉 Haz clic para descargar el PDF</a>'
        )
        st.markdown(link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
