import os, datetime as dt, base64, tempfile
import pandas as pd
import streamlit as st
from fredapi import Fred
import feedparser
from textblob import TextBlob
import weasyprint

# --------  Configuración --------
# Intenta primero con st.secrets (Streamlit Cloud); si no existe, con os.environ
API_KEY = st.secrets.get("FRED_API_KEY") or os.getenv("FRED_API_KEY")
if not API_KEY:
    st.error("❌ No se encontró FRED_API_KEY en st.secrets ni en os.environ")
    st.stop()

fred = Fred(api_key=API_KEY)

# Indicadores macro (código FRED → etiqueta)
SERIES = {
    "NAPMNOI": "PMI",
    "PCEPI"  : "PCE_YoY",
    "UNRATE" : "Unemployment",
    "T5YIFR" : "Breakeven_5y5y"
}

# --------  Funciones --------
@st.cache_data
def get_macro():
    dfs = []
    for code, name in SERIES.items():
        s = fred.get_series(code, observation_start="2000-01-01")
        s.index = pd.to_datetime(s.index)
        s.name = name
        dfs.append(s)
    return pd.concat(dfs, axis=1)

@st.cache_data
def get_sentiment():
    RSS = "http://feeds.reuters.com/reuters/businessNews"
    feed = feedparser.parse(RSS)
    rows = []
    for e in feed.entries[:50]:
        date = dt.datetime(*e.published_parsed[:6])
        score = TextBlob(e.title).sentiment.polarity
        rows.append((date, e.title, score))
    df = pd.DataFrame(rows, columns=["time","title","score"])
    df["hour"] = df["time"].dt.floor("H")
    return df

def to_pdf(df_latest):
    # Genera un HTML con la tabla de los últimos datos
    html = f"""
    <h1>Macro Snapshot</h1>
    <p>Fecha: {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC</p>
    {df_latest.to_frame().to_html(border=0)}
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    weasyprint.HTML(string=html).write_pdf(tmp.name)
    return tmp.name

# --------  Interfaz --------
def main():
    st.title("📊 Market Pulse Lite")
    st.caption(f"Actualizado: {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC")

    # 1. Macro chart + tabla
    macro = get_macro()
    st.subheader("Indicadores macro (últimos 3 años)")
    st.line_chart(macro.tail(36))
    latest = macro.tail(1).T
    latest.columns = ["Value"]
    st.subheader("Último dato disponible")
    st.table(latest)

    # 2. Sentiment chart
    sentiment = get_sentiment().groupby("hour")["score"].mean().to_frame()
    st.subheader("Sentimiento Reuters (últimas 24 h)")
    st.line_chart(sentiment.tail(24))

    # 3. PDF download
    if st.button("📄 Descargar PDF"):
        path = to_pdf(latest["Value"])
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="macro_snapshot.pdf">Bajar PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
