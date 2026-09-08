import pandas as pd


def calcular_sma(
    df: pd.DataFrame, periodo: int = 20, columna: str = "close"
) -> pd.Series:
    """Media Móvil Simple: promedio aritmético de los últimos N cierres."""
    return df[columna].rolling(window=periodo).mean()
