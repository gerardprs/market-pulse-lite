# app.py — Market Pulse Lite (usando requests, con fixes para series y datetime)

import datetime as dt
import base64
import tempfile

import requests
import pandas as pd
import streamlit as st
import feedparser
from textblob import TextBlob
import weasyprint

# ———————————————
# CLAVE FRED DIRECTA (versión demo)
API_KEY = "62deb3b46aa3632a30ee4f2885c1f32a"
# ———————————————

# ---------------------------------------
# Mapear sólo IDs válidos en FRED
# ---------------------------------------
SERIES = {
    "NAPMNOI": "PMI",           # ISM Manufacturing PMI
    "PCEPI"  : "PCE_YoY",       # Personal Consumption Expenditures YoY
    "UNRATE" : "Unemployment",  # Unemployment Rate
    "T5YIFR" : "Breakeven_5y5y" # 5-year Breakeven Inflation
}

@st.cache_data
def get_macro():
    dfs = []
    for code, label in SERIES.items():
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={code}&api_key={API_KEY}&file_type=json"
        )
        r = requests.get(url)
        data = r.json()
        obs = data.get("observations")
        if not obs:
            st.warning(f"⚠️ Serie {code} no existe o no está disponible.")
            continue

        df = pd.DataFrame(obs)
        df["date"]  = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.set_index("date")["value"].rename(label)
        dfs.append(s)

    return pd.concat(dfs, axis=1) if dfs else pd.DataFrame()

@st.cache_data
def get_sentiment():
    RSS = "http://feeds.reuters.com/reuters/businessNews"
    feed = feedparser.parse(RSS)
    rows = []
    for entry in feed.entries[:50]:
        # usar published_parsed para obtener tupla de fecha
        if not hasattr(entry, "published_parsed"):
            continue
        ts = dt.datetime(*entry.published_parsed[:6])
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
        st.error("No se pudo cargar ningún indicador macro.")
    else:
        st.subheader("Indicadores macro (últimos 3 años)")
        st.line_chart(macro.tail(36))

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
            'download="macro_snapshot.pdf">👉 Haz clic para bajar el PDF</a>'
        )
        st.markdown(link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
