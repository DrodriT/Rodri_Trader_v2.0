import numpy as np
import pandas as pd


def calcular_dm(df: pd.DataFrame, periodo: int = 14) -> pd.DataFrame:
    """Directional Movement System (+DI, -DI y ADX) para fuerza y dirección de tendencia."""
    high = df["high"]
    low = df["low"]

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    close_prev = df["close"].shift(1)
    tr = pd.concat(
        [high - low, (high - close_prev).abs(), (low - close_prev).abs()],
        axis=1,
    ).max(axis=1)

    atr_smooth = tr.ewm(
        alpha=1 / periodo, min_periods=periodo, adjust=False
    ).mean()
    plus_dm_smooth = (
        pd.Series(plus_dm, index=df.index)
        .ewm(alpha=1 / periodo, min_periods=periodo, adjust=False)
        .mean()
    )
    minus_dm_smooth = (
        pd.Series(minus_dm, index=df.index)
        .ewm(alpha=1 / periodo, min_periods=periodo, adjust=False)
        .mean()
    )

    plus_di = 100 * (plus_dm_smooth / atr_smooth)
    minus_di = 100 * (minus_dm_smooth / atr_smooth)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1 / periodo, min_periods=periodo, adjust=False).mean()

    return pd.DataFrame(
        {"+DI": plus_di, "-DI": minus_di, "ADX": adx}, index=df.index
    )
