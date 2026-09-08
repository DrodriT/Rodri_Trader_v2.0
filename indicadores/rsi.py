import pandas as pd


def calcular_rsi(
    df: pd.DataFrame, periodo: int = 14, columna: str = "close"
) -> pd.Series:
    """Índice de Fuerza Relativa (RSI de Wilder)."""
    delta = df[columna].diff()

    ganancia = delta.clip(lower=0)
    perdida = -1 * delta.clip(upper=0)

    # Suavizado exponencial de Wilder (alpha = 1 / periodo)
    avg_gain = ganancia.ewm(
        alpha=1 / periodo, min_periods=periodo, adjust=False
    ).mean()
    avg_loss = perdida.ewm(
        alpha=1 / periodo, min_periods=periodo, adjust=False
    ).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
