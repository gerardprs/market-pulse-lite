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
        # usar published_parsed pa_

