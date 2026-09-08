import pandas as pd


def calcular_vwap(df: pd.DataFrame) -> pd.Series:
    """Precio Promedio Ponderado por Volumen (Volume Weighted Average Price)."""
    precio_tipico = (df["high"] + df["low"] + df["close"]) / 3
    pv = precio_tipico * df["volume"]
    vwap = pv.cumsum() / df["volume"].cumsum()
    return vwap
