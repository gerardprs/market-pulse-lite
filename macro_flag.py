#!/usr/bin/env python
import os
import datetime as dt
import numpy as np
import pandas as pd
from fredapi import Fred

def main():
    # 1) Configuración
    API_KEY = os.getenv("FRED_API_KEY")
    if not API_KEY:
        raise RuntimeError("Define FRED_API_KEY en variables de entorno")
    fred = Fred(api_key=API_KEY)

    # 2) Series a descargar (código FRED → etiqueta)
    SERIES = {
        "NAPMNOI":   "PMI manufacturero (ISM)",
        "PCEPI":     "PCE YoY",
        "UNRATE":    "Tasa desempleo",
        "T5YIFR":    "Breakeven 5y5y",
        "MANEMP":    "ISM New Orders"
    }

    # 3) Descargar y concatenar en DataFrame
    dfs = []
    for code, label in SERIES.items():
        s = fred.get_series(code, observation_start="2000-01-01")
        s.name = label
        dfs.append(s)
    df = pd.concat(dfs, axis=1).dropna()

    # 4) Calcular z-score y semáforos
    z = (df - df.mean()) / df.std()
    last_z = z.iloc[-1]
    flags = pd.cut(
        last_z,
        bins=[-np.inf, -1, 1, np.inf],
        labels=["🔴 Rojo", "🟡 Ámbar", "🟢 Verde"]
    )

    # 5) Preparar tabla de salida
    out = pd.DataFrame({
        "Indicador": last_z.index,
        "Z-score": last_z.values.round(2),
        "Semaphore": flags.values
    })

    # 6) Exportar a Excel
    today = dt.datetime.utcnow().strftime("%Y%m%d")
    fname = f"macro_flag_{today}.xlsx"
    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        out.to_excel(writer, sheet_name="Semáforo", index=False)
    print(f"✅ Informe generado: {fname}")

if __name__ == "__main__":
    main()

