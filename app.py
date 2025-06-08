# app.py  —  Market Pulse Lite  (versión mínima funcional)

import os, datetime as dt
import pandas as pd
import streamlit as st
from fredapi import Fred
from dotenv import load_dotenv

# --------  Configuración --------
load_dotenv()                                 # lee variables .env o Secrets
fred = Fred(api_key=os.getenv("FRED_API_KEY"))

SERIES = {                                    # código FRED : nombre visible
    "NAPMNOI": "PMI",
    "PCEPI"  : "PCE_yoy",
    "UNRATE" : "Unemployment",
    "T5YIFR" : "Breakeven_5y5y"
}

# --------  Funciones --------
@st.cache_data
def get_data():
    dfs = []
    for code, name in SERIES.items():
        s = fred.get_series(code, observation_start="2000-01-01")
        s.index = pd.to_datetime(s.index)
        s.name = name
        dfs.append(s)
    return pd.concat(dfs, axis=1)

# --------  Interfaz --------
def main():
    st.title("📊 Market Pulse Lite — Macro Scanner")
    st.caption(f"Actualizado: {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC")

    df = get_data()

    st.write("### Gráfico (últimos 3 años)")
    st.line_chart(df.tail(36))                # 36 meses ≈ 3 años

    st.write("### Último dato disponible")
    st.dataframe(df.tail(1).T)                # muestra la fila más reciente

if __name__ == "__main__":
    main()

