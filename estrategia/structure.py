import pandas as pd

import config

# Puntuación parcial cuando no hay breakout pero la estructura se mantiene sana.
# Valor fijo definido por el modelo V1.0 (no proporcional a PUNTOS_STRUCTURE,
# para respetar exactamente la especificación: 15 / 8 / 0 puntos).
PUNTOS_ESTRUCTURA_PARCIAL = 8.0


def calcular_niveles_estructura(df: pd.DataFrame, periodo: int = None) -> pd.DataFrame:
    """
    Calcula el máximo y el mínimo de las últimas `periodo` velas,
    EXCLUYENDO la vela actual (mediante shift(1)).

    Devuelve un DataFrame con dos columnas nuevas: 'highest_N' y 'lowest_N',
    listas para unir (join) al DataFrame original.
    """
    periodo = periodo or config.HIGHEST_LOWEST_PERIODO

    highest = df["high"].rolling(window=periodo).max().shift(1)
    lowest = df["low"].rolling(window=periodo).min().shift(1)

    return pd.DataFrame(
        {
            f"highest_{periodo}": highest,
            f"lowest_{periodo}": lowest,
        },
        index=df.index,
    )


def puntuar_structure(df: pd.DataFrame, direccion: str) -> float:
    """
    Puntúa el componente STRUCTURE (breakout de máximos/mínimos) para la
    última vela de df.

    LONG:
        Close > Highest_N (excluyendo vela actual)          -> PUNTOS_STRUCTURE (15)
        Close > EMA_lenta Y Low actual > Low anterior         -> 8 pts
        Si no                                                 -> 0 pts

    SHORT: condiciones espejo con Lowest_N y High.

    Requiere que df tenga ya las columnas 'close', 'high', 'low', 'EMA_lenta'
    y los niveles ('highest_N', 'lowest_N') calculados con
    calcular_niveles_estructura().
    """
    periodo = config.HIGHEST_LOWEST_PERIODO
    col_highest = f"highest_{periodo}"
    col_lowest = f"lowest_{periodo}"

    # Necesitamos al menos 2 velas: la actual y la anterior
    if len(df) < 2:
        return 0.0

    actual = df.iloc[-1]
    anterior = df.iloc[-2]

    if direccion == "LONG":
        if pd.notna(actual[col_highest]) and actual["close"] > actual[col_highest]:
            return float(config.PUNTOS_STRUCTURE)  # Breakout alcista confirmado

        if actual["close"] > actual["EMA_lenta"] and actual["low"] > anterior["low"]:
            return PUNTOS_ESTRUCTURA_PARCIAL  # Estructura sana, sin ruptura

        return 0.0

    elif direccion == "SHORT":
        if pd.notna(actual[col_lowest]) and actual["close"] < actual[col_lowest]:
            return float(config.PUNTOS_STRUCTURE)  # Breakout bajista confirmado

        if actual["close"] < actual["EMA_lenta"] and actual["high"] < anterior["high"]:
            return PUNTOS_ESTRUCTURA_PARCIAL  # Estructura sana, sin ruptura

        return 0.0

    return 0.0