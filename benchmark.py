#!/usr/bin/env python
import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf

def compute_te_ir(port_rets, bench_rets):
    # Alineamos fechas
    p, b = port_rets.align(bench_rets, join="inner")
    excess = p - b
    te = excess.std() * np.sqrt(252)
    ann_excess = excess.mean() * 252
    ir = ann_excess / te if te != 0 else np.nan
    return te, ir

def main():
    if len(sys.argv) < 2:
        print("Uso: python benchmark.py portfolio.csv")
        sys.exit(1)

    path = sys.argv[1]
    df = pd.read_csv(path)  # columnas: ticker,weight (en decimales, p.ej. 0.25)
    weights = df.set_index("ticker")["weight"]

    # Benchmarks fijos
    BENCH = ["SPY", "AGG", "QQQ"]

    # Descargar precios (1 año diario)
    tickers = list(weights.index) + BENCH
    prices = yf.download(tickers, period="1y", progress=False)["Close"].dropna(how="all")

    # Calcular retornos
    rets = prices.pct_change().dropna()
    port_rets = (rets[weights.index] * weights).sum(axis=1)
    bench_rets = rets[ BENCH ].mean(axis=1)

    # Métricas
    te, ir = compute_te_ir(port_rets, bench_rets)

    # Generar reporte Excel
    os.makedirs("reports", exist_ok=True)
    fname = f"reports/benchmark_report_{pd.Timestamp.utcnow():%Y%m%d}.xlsx"
    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        pd.DataFrame({
            "Tracking Error (ann.)": [te],
            "Information Ratio": [ir]
        }, index=["Portfolio"]).to_excel(writer, sheet_name="Metrics")
        prices.to_excel(writer, sheet_name="Prices")
    print(f"✅ Benchmark report: {fname}")

if __name__ == "__main__":
    main()
