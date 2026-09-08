import numpy as np
import pandas as pd
from indicadores import (
    calcular_atr,
    calcular_dm,
    calcular_ema,
    calcular_rsi,
    calcular_sma,
    calcular_stop_loss_atr,
    calcular_vwap,
)

# 1. Simulación de 100 velas
np.random.seed(42)
precios_cierre = 50000 + np.cumsum(np.random.randn(100) * 150)

df = pd.DataFrame(
    {
        "open": precios_cierre + np.random.randn(100) * 20,
        "high": precios_cierre + np.random.uniform(50, 200, 100),
        "low": precios_cierre - np.random.uniform(50, 200, 100),
        "close": precios_cierre,
        "volume": np.random.uniform(10, 100, 100),
    }
)

# 2. Aplicación de cada módulo
df["SMA_20"] = calcular_sma(df, periodo=20)
df["EMA_20"] = calcular_ema(df, periodo=20)
df["VWAP"] = calcular_vwap(df)
df["RSI_14"] = calcular_rsi(df, periodo=14)
df["ATR_14"] = calcular_atr(df, periodo=14)

dmi = calcular_dm(df, periodo=14)
df["+DI"] = dmi["+DI"]
df["-DI"] = dmi["-DI"]
df["ADX"] = dmi["ADX"]

# 3. Mostrar últimos resultados
print("=== ÚLTIMAS 3 VELAS CALCULADAS ===")
print(df[["close", "SMA_20", "EMA_20", "VWAP", "RSI_14", "ADX"]].tail(3).round(2))

# 4. Stop Loss
precio_actual = df["close"].iloc[-1]
atr_actual = df["ATR_14"].iloc[-1]
sl = calcular_stop_loss_atr(precio_actual, atr_actual, multiplicador=2.0)
print(f"\nPrecio actual: ${precio_actual:,.2f} | Stop Loss (2x ATR): ${sl:,.2f}")
