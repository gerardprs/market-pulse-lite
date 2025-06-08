#!/usr/bin/env python
import datetime as dt
import pandas as pd
from fredapi import Fred

def main():
    # 1) Clave FRED embebida
    API_KEY = "62deb3b46aa3632a30ee4f2885c1f32a"
    fred = Fred(api_key=API_KEY)

    # 2) Series a descargar
    SERIES = {
        "NAPMNOI": "PMI manufacturero (ISM)",
        "PCEPI":   "PCE YoY",
        "UNRATE":  "Tasa desempleo",
        "T5YIFR":  "Breakeven 5y5y",
        "MANEMP":  "ISM New Orders"
    }

    # 3) Descargar datos
    dfs = []
    for code, label in SERIES.items():
        s = fred.get_series(code, observation_start="2000-01-01")
        s.name = label
        dfs.append(s)
    df = pd.concat(dfs, axis=1).dropna()

    # 4) Calcular z-score y semáforos
    z = (df - df.mean()) / df.std()
    last_z = z.iloc[-1]
    bins = [-float("inf"), -1, 1, float("inf")]
    labels = ["🔴 Rojo", "🟡 Ámbar", "🟢 Verde"]
    flags = pd.cut(last_z, bins=bins, labels=labels)

    # 5) Preparar tabla de salida
    out = pd.DataFrame({
        "Indicador": last_z.index,
        "Z-score":   last_z.values.round(2),
        "Semaphore": flags.values
    })

    # 6) Exportar a Excel
    today = dt.datetime.utcnow().strftime("%Y%m%d")
    fname = f"macro_flag_{today}.xlsx"
    out.to_excel(fname, index=False)
    print(f"✅ Informe generado: {fname}")

if __name__ == "__main__":
    main()
