import pandas as pd


def calcular_ema(
    df: pd.DataFrame, periodo: int = 20, columna: str = "close"
) -> pd.Series:
    """Media Móvil Exponencial: da mayor ponderación a los precios más recientes."""
    return df[columna].ewm(span=periodo, adjust=False).mean()
