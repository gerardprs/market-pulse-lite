# dashboard.py  — Enhanced Liquid Portfolio Monitor

import datetime as dt
import random
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.express as px
from statsmodels.regression.rolling import RollingOLS
from sklearn.decomposition import PCA
from fpdf import FPDF

# -------- CONFIGURACIÓN --------
st.set_page_config(
    page_title="Liquid Portfolio Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Universo de ETFs (añade o quita tickers a tu gusto)
UNIVERSE = {
    "SPY": "S&P 500",
    "AGG": "US Aggregate Bond",
    "GLD": "Gold ETF",
    "EEM": "Emerging Mkts",
    "FXE": "EUR/USD ETF",
    "TLT": "20+ Year Treasury",
    "IEF": "7–10 Year Treasury",
    "TIP": "TIPS ETF",
    "QQQ": "Nasdaq 100",
    "DBC": "Commodities Index"
}

BENCHMARKS = {
    "SPY": "S&P 500",
    "AGG": "US Agg Bond",
    "QQQ": "Nasdaq 100"
}


# -------- FUNCIONES AUXILIARES --------
@st.cache_data
def fetch_prices(tickers, period="1y"):
    df = yf.download(list(tickers), period=period, progress=False)["Close"]
    df = df.dropna(how="all")
    return df

def random_portfolio(universe, n):
    tickers = random.sample(list(universe.keys()), n)
    weights = {t: 1/n for t in tickers}
    return weights

def compute_betas(prices, factors, window=60):
    rets = prices.pct_change().dropna()
    betas = {}
    for t in rets.columns:
        Y = rets[t]
        X = factors.loc[Y.index]
        model = RollingOLS(Y, st.add_constant(X), window=window)
        rres = model.fit()
        betas[t] = rres.params.iloc[-1, 1:]  # skip constant
    return pd.DataFrame(betas).T

def pca_yield(ytm_df):
    pca = PCA(n_components=3)
    comps = pca.fit_transform(ytm_df.dropna())
    dfc = pd.DataFrame(
        comps,
        index=ytm_df.dropna().index,
        columns=["Nivel", "Pendiente", "Curvatura"]
    )
    return dfc

def make_pdf(portfolio, betas, pca_last, sentiment_mom):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Liquid Portfolio Snapshot", ln=1, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Fecha: {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "1. Cartera Aleatoria", ln=1)
    pdf.set_font("Arial", "", 11)
    for t, w in portfolio.items():
        pdf.cell(0, 6, f"• {t}: {w:.2%}", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "2. Betas Factores (última ventana)", ln=1)
    pdf.set_font("Arial", "", 11)
    for t, row in betas.iterrows():
        vals = ", ".join(f"{f}:{row[f]:.2f}" for f in row.index)
        pdf.cell(0, 6, f"• {t}: {vals}", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "3. PCA Yield Curve (último dato)", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Nivel: {pca_last['Nivel']:.2f}", ln=1)
    pdf.cell(0, 6, f"Pendiente: {pca_last['Pendiente']:.2f}", ln=1)
    pdf.cell(0, 6, f"Curvatura: {pca_last['Curvatura']:.2f}", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "4. Sentiment Momentum", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"{sentiment_mom:.2f}", ln=1)

    outfile = f"reports/snapshot_{dt.datetime.utcnow():%Y%m%d_%H%M}.pdf"
    pdf.output(outfile)
    return outfile


# -------- BARRA LATERAL --------
st.sidebar.header("Configuración de Cartera")
n_assets = st.sidebar.slider(
    "Número de activos",
    min_value=2, max_value=10, value=4, step=1,
    help="Selecciona cuántos activos incluir en la cartera aleatoria"
)
if st.sidebar.button("🃏 Generar Cartera"):
    # Generar y guardar en estado
    portfolio = random_portfolio(UNIVERSE, n_assets)
    st.session_state["portfolio"] = portfolio
    st.experimental_rerun()

# Si no existe aún, crea una cartera inicial
if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = random_portfolio(UNIVERSE, n_assets)

portfolio = st.session_state["portfolio"]


# -------- PANTALLA PRINCIPAL --------
st.title("💧 Enhanced Liquid Portfolio Monitor")
st.markdown(
    "Este dashboard te permite generar carteras aleatorias, compararlas "
    "con benchmarks, analizar factores y curvas de rendimiento, y extraer "
    "insights de sentimiento."
)

# 1. Mostrar cartera
st.subheader("1️⃣ Cartera Aleatoria")
st.write("Selecciona el número de activos y pulsa **Generar Cartera**:")
cols = st.columns(len(portfolio))
for idx, (t, w) in enumerate(portfolio.items()):
    with cols[idx]:
        st.metric(label=t, value=f"{w:.2%}", delta="Peso igual")

# 2. Benchmarking
st.subheader("2️⃣ Benchmarking vs Indices")
prices = fetch_prices(list(portfolio.keys()) + list(BENCHMARKS.keys()), period="1y")
port_prices = prices[list(portfolio.keys())]
bench_prices = prices[list(BENCHMARKS.keys())]

# Plot Retour
c_port = (port_prices.pct_change()+1).cumprod().dropna()
c_bench = (bench_prices.pct_change()+1).cumprod().dropna()
fig = px.line(
    pd.concat([c_port.mean(axis=1), c_bench], axis=1),
    labels={"value": "Wealth", "index": "Fecha"},
    title="Evolución Cartera vs Benchmarks"
)
st.plotly_chart(fig, use_container_width=True)

# 3. Factor Attribution
st.subheader("3️⃣ Betas Factores (Rolling 60d)")
# Simplicidad: consideramos solo el promedio de benchmarks como factor mercado
factors = bench_prices.pct_change().dropna().mean(axis=1).to_frame("Market")
betas = compute_betas(port_prices, factors)
st.dataframe(betas.style.highlight_max(axis=1, color="lightgreen"))

# 4. PCA Yield Curve
st.subheader("4️⃣ PCA de la Curva UST")
# Usamos TLT, IEF y TIP como proxy de 30a, 7-10a y TIPS
ytm = fetch_prices({"^TNX":"30Y","^IEF":"7-10Y","^TIP":"TIPS"}, period="3y")
pca_df = pca_yield(ytm)
fig2 = px.line(pca_df, title="Componentes PCA (Nivel, Pendiente, Curvatura)")
st.plotly_chart(fig2, use_container_width=True)

# 5. Sentiment Momentum
st.subheader("5️⃣ Sentiment Momentum")
# Reutilizamos texto de antes
sent = pd.DataFrame(
    [(dt.datetime(*e.published_parsed[:6]), TextBlob(e.title).sentiment.polarity)
     for e in __import__("feedparser").parse("http://feeds.reuters.com/reuters/businessNews").entries[:50]],
    columns=["time","score"]
).set_index("time")
mom = sent["score"].diff(6).fillna(0).iloc[-1]
st.metric("Cambio en sentimiento (6h)", f"{mom:.2f}", delta_color="inverse")

# 6. Exportar PDF
st.subheader("📄 Generar Reporte Ejecutivo")
if st.button("Descargar Snapshot PDF"):
    pdf_file = make_pdf(
        portfolio,
        betas,
        pca_df.tail(1).iloc[0],
        mom
    )
    with open(pdf_file, "rb") as f:
        st.download_button(
            "👉 Descargar PDF",
            data=f,
            file_name=pdf_file.split("/")[-1],
            mime="application/pdf"
        )
