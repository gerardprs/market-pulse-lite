# dashboard.py — Enhanced Liquid Portfolio Monitor

import os
import datetime as dt
import random
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.express as px
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS
from sklearn.decomposition import PCA
from fpdf import FPDF
import feedparser
from textblob import TextBlob

# -------- CONFIGURACIÓN --------
st.set_page_config(
    page_title="Liquid Portfolio Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)
os.makedirs("reports", exist_ok=True)

# -------- UNIVERSOS Y BENCHMARKS --------
UNIVERSE = {
    "SPY": "S&P 500", "AGG": "US Agg Bond",
    "GLD": "Gold ETF", "EEM": "Emerging Mkts",
    "FXE": "EUR/USD ETF", "TLT": "20+ Year UST",
    "IEF": "7–10 Year UST", "TIP": "TIPS ETF",
    "QQQ": "Nasdaq 100", "DBC": "Commodities"
}
BENCH = ["SPY", "AGG", "QQQ"]

# -------- FUNCIONES AUXILIARES --------
@st.cache_data
def fetch_prices(tickers, period="1y"):
    df = yf.download(tickers, period=period, progress=False)["Close"]
    return df.dropna(how="all")

def random_portfolio(universe, n):
    picks = random.sample(list(universe.keys()), n)
    w = {t: 1/n for t in picks}
    return w

def compute_te_ir(port_prices, bench_prices):
    rets_p = port_prices.pct_change().dropna().mean(axis=1)
    rets_b = bench_prices.pct_change().dropna().mean(axis=1)
    excess = rets_p.align(rets_b, join="inner")[0] - rets_b.align(rets_p, join="inner")[0]
    te = excess.std() * np.sqrt(252)
    ann_excess = excess.mean() * 252
    ir = ann_excess / te if te != 0 else np.nan
    return te, ir

def compute_betas(port_prices, factors, window=60):
    rets = port_prices.pct_change().dropna()
    betas = {}
    for t in rets.columns:
        Y = rets[t]
        X = sm.add_constant(factors.loc[Y.index])
        model = RollingOLS(Y, X, window=window)
        res = model.fit()
        last = res.params.iloc[-1].drop("const")
        betas[t] = last
    return pd.DataFrame(betas).T

@st.cache_data
def pca_yield_curve(tickers, period="3y"):
    df = fetch_prices(tickers, period=period)
    # rename columns
    df = df.rename(columns={tickers[0]:"Nivel", tickers[1]:"Pendiente", tickers[2]:"Curvatura"})
    comp = PCA(n_components=3).fit_transform(df.dropna())
    return pd.DataFrame(comp, index=df.dropna().index, columns=["Nivel","Pendiente","Curvatura"])

@st.cache_data
def get_sentiment_momentum():
    feed = feedparser.parse("http://feeds.reuters.com/reuters/businessNews")
    rows = []
    for e in feed.entries[:50]:
        if hasattr(e, "published_parsed"):
            ts = dt.datetime(*e.published_parsed[:6])
        else:
            ts = dt.datetime.utcnow()
        score = TextBlob(e.title).sentiment.polarity
        rows.append({"time":ts, "score":score})
    df = pd.DataFrame(rows).set_index("time").resample("H").mean().fillna(0)
    # momentum = última hora – anterior
    mom = df["score"].diff().iloc[-1]
    return df, mom

def make_pdf(portfolio, te, ir, betas, pca_last, sentiment_mom):
    now = dt.datetime.utcnow().strftime("%Y%m%d_%H%M")
    path = f"reports/snapshot_{now}.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Liquid Portfolio Snapshot", ln=1, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Fecha UTC: {dt.datetime.utcnow():%Y-%m-%d %H:%M}", ln=1)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "1. Cartera Aleatoria", ln=1)
    pdf.set_font("Arial", "", 12)
    for t,w in portfolio.items():
        pdf.cell(0,6,f"• {t}: {w:.2%}", ln=1)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "2. TE / IR", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0,6,f"• Tracking Error: {te:.2%}", ln=1)
    pdf.cell(0,6,f"• Info Ratio: {ir:.2f}", ln=1)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "3. Betas Factores", ln=1)
    pdf.set_font("Arial", "", 12)
    for t,row in betas.iterrows():
        vals = ", ".join(f"{f}:{row[f]:.2f}" for f in row.index)
        pdf.cell(0,6,f"• {t}: {vals}", ln=1)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "4. PCA Yield Curve", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0,6,f"Nivel: {pca_last['Nivel']:.2f}", ln=1)
    pdf.cell(0,6,f"Pendiente: {pca_last['Pendiente']:.2f}", ln=1)
    pdf.cell(0,6,f"Curvatura: {pca_last['Curvatura']:.2f}", ln=1)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 14); pdf.cell(0, 8, "5. Sentiment Momentum", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0,6,f"Cambio (última hora): {sentiment_mom:.2f}", ln=1)

    pdf.output(path)
    return path

# -------- BARRA LATERAL --------
st.sidebar.header("🔧 Configuración de Cartera")
n = st.sidebar.slider("Número de activos", 2, 10, 4)
if st.sidebar.button("🃏 Generar Cartera"):
    st.session_state.portfolio = random_portfolio(UNIVERSE, n)
    st.experimental_rerun()

portfolio = st.session_state.get("portfolio") or random_portfolio(UNIVERSE, n)

# -------- PANTALLA PRINCIPAL --------
st.title("💧 Enhanced Liquid Portfolio Monitor")
st.markdown("**Paso 1:** Genera una cartera aleatoria y compara con benchmarks. Usa la barra lateral.")

# 1️⃣ Cartera Aleatoria
st.header("1️⃣ Cartera Aleatoria")
cols = st.columns(len(portfolio))
for col, (t,w) in zip(cols, portfolio.items()):
    col.metric(label=UNIVERSE[t], value=f"{w:.2%}", delta="Peso igual", delta_color="normal")

# 2️⃣ Benchmarking
st.header("2️⃣ Benchmarking vs Índices")
prices = fetch_prices(list(portfolio.keys()) + BENCH, period="1y")
pp = prices[list(portfolio.keys())]; bp = prices[BENCH]
# Evolución acumulada
cp = (pp.pct_change()+1).cumprod().dropna().mean(axis=1)
cb = (bp.pct_change()+1).cumprod().dropna().mean(axis=1)
te, ir = compute_te_ir(pp, bp)
st.metric("Tracking Error anualizado", f"{te:.2%}")
st.metric("Information Ratio", f"{ir:.2f}")
fig = px.line(pd.concat({"Cartera":cp, "Bench":cb}, axis=1),
              title="Evolución Cartera vs Benchmark")
st.plotly_chart(fig, use_container_width=True)

# 3️⃣ Betas Factores
st.header("3️⃣ Betas Rolling (60d)")
factors = bp.pct_change().dropna().mean(axis=1).to_frame("Market")
betas = compute_betas(pp, factors)
st.markdown("Media móvil de 60 días contra el factor Market.")
figb = px.bar(betas.reset_index().melt(id_vars="index"),
              x="index", y="value", color="variable",
              labels={"index":"Activo","value":"Beta","variable":"Factor"},
              title="Beta por activo y factor")
st.plotly_chart(figb, use_container_width=True)

# 4️⃣ PCA Yield Curve
st.header("4️⃣ PCA Curva UST")
pca_df = pca_yield_curve(["^TNX","^FVX","^IRX"], period="3y")
st.markdown("Componentes PCA: Nivel, Pendiente, Curvatura.")
figp = px.line(pca_df, title="PCA Yield Curve (3 años)")
st.plotly_chart(figp, use_container_width=True)

# 5️⃣ Sentiment Momentum
st.header("5️⃣ Sentiment Momentum")
sent_df, mom = get_sentiment_momentum()
st.markdown("Delta horario del score de sentimiento (Reuters Business).")
st.metric("Momentum sentimiento (última hora)", f"{mom:.2f}")
figs = px.line(sent_df, y="score", title="Sentiment Score por hora")
st.plotly_chart(figs, use_container_width=True)

# 📄 Reporte Ejecutivo
st.header("📄 Generar Reporte Ejecutivo")
if st.button("Descargar Snapshot PDF"):
    pdf_path = make_pdf(portfolio, te, ir, betas, pca_df.iloc[-1], mom)
    with open(pdf_path, "rb") as f:
        st.download_button("👉 Descargar PDF", f, file_name=os.path.basename(pdf_path), mime="application/pdf")

