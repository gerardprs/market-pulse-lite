#!/usr/bin/env python
import streamlit as st
import subprocess, tempfile, os

st.set_page_config(page_title="Portafolio Python", layout="wide")
st.title("📚 Mi Portafolio de Mini‐Proyectos")

st.markdown("""
Este escaparate agrupa **3 mini‐proyectos** listos para demostrar tus habilidades de Python:

- **Macro Semáforo Diario**  
- **Benchmark Calculator**  
- **News‐Alert Sentiment**
""")

tab1, tab2, tab3 = st.tabs([
    "1️⃣ Macro Semáforo",
    "2️⃣ Benchmark Calc",
    "3️⃣ News Alert"
])

# Tab 1
with tab1:
    st.header("1️⃣ Macro Semáforo Diario")
    st.write("""
    - Descarga 5 series FRED  
    - Calcula z‐score + semáforos 🔴🟡🟢  
    - Exporta un Excel con la tabla de flags
    """)
    if st.button("▶️ Ejecutar macro_flag.py"):
        proc = subprocess.run(["python","macro_flag.py"], capture_output=True, text=True)
        st.code(proc.stdout or proc.stderr)
        files = sorted(f for f in os.listdir() if f.startswith("macro_flag_") and f.endswith(".xlsx"))
        if files:
            f = files[-1]
            with open(f,"rb") as fp:
                st.download_button("⬇️ Descargar Excel", fp, file_name=f, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Tab 2
with tab2:
    st.header("2️⃣ Benchmark Calculator")
    st.write("""
    - Sube un CSV con `ticker,weight`  
    - Calcula Tracking Error & Info Ratio  
    - Exporta reporte Excel
    """)
    csv = st.file_uploader("📁 Subir portfolio.csv", type="csv")
    if csv:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        open(tmp,"wb").write(csv.getvalue())
        proc = subprocess.run(["python","benchmark.py", tmp], capture_output=True, text=True)
        st.code(proc.stdout or proc.stderr)
        rpt = sorted(os.listdir("reports"))[-1]
        with open(os.path.join("reports",rpt),"rb") as fp:
            st.download_button("⬇️ Descargar Reporte", fp, file_name=rpt, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Tab 3
with tab3:
    st.header("3️⃣ News‐Alert Sentiment")
    st.write("""
    - Lee titulares RSS de Reuters  
    - Calcula polaridad por hora  
    - Si baja de umbral → alerta  
    """)
    th = st.slider("Umbral de alerta", -1.0, 1.0, -0.2, 0.05)
    if st.button("🔍 Ejecutar news_alert.py"):
        proc = subprocess.run(["python","news_alert.py", str(th)], capture_output=True, text=True)
        st.code(proc.stdout or proc.stderr)
        if "⚠️" in proc.stdout:
            st.error("🔴 Se disparó una alerta")
        else:
            st.success("✅ Todo OK")

st.markdown("---")
st.caption("Hecho con ❤️ usando Python y Streamlit")
