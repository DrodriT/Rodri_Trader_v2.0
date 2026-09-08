import pandas as pd


def calcular_atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """Average True Range (ATR): mide la volatilidad media del mercado."""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Suavizado de Wilder
    atr = tr.ewm(alpha=1 / periodo, min_periods=periodo, adjust=False).mean()
    return atr


def calcular_stop_loss_atr(
    precio_entrada: float,
    atr_valor: float,
    multiplicador: float = 1.5,
    direccion: str = "LONG",
) -> float:
    """Calcula el Stop Loss dinámico según la volatilidad."""
    if direccion.upper() == "LONG":
        return precio_entrada - (atr_valor * multiplicador)
    elif direccion.upper() == "SHORT":
        return precio_entrada + (atr_valor * multiplicador)
    else:
        raise ValueError("La dirección debe ser 'LONG' o 'SHORT'")
