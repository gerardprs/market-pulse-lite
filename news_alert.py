#!/usr/bin/env python
import sys
import datetime as dt
import pandas as pd
import feedparser
from textblob import TextBlob

def main():
    # Umbral opcional via argumento
    threshold = float(sys.argv[1]) if len(sys.argv)>1 else -0.2

    # 1) Descargar titulares Reuters Business
    RSS = "http://feeds.reuters.com/reuters/businessNews"
    feed = feedparser.parse(RSS)

    # 2) Calcular polaridad y agrupar por hora
    rows = []
    for e in feed.entries[:50]:
        if hasattr(e, "published_parsed"):
            ts = dt.datetime(*e.published_parsed[:6])
        else:
            ts = dt.datetime.utcnow()
        score = TextBlob(e.title).sentiment.polarity
        rows.append({"time":ts, "score":score})
    df = (
        pd.DataFrame(rows)
          .set_index("time")
          .resample("H")
          .mean()
          .fillna(0)
    )

    # 3) Último valor vs umbral
    last = df["score"].iloc[-1]
    print(f"Hora: {df.index[-1]} UTC — Sentiment: {last:.2f}")
    if last < threshold:
        print(f"⚠️ Alerta: Sentiment {last:.2f} bajo {threshold:.2f}")
    else:
        print("✅ Sentiment OK")

if __name__ == "__main__":
    main()
