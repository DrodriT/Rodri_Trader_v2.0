import pandas as pd

import config
from estrategia.structure import calcular_niveles_estructura


def calcular_stop_loss(df_5m: pd.DataFrame, direccion: str) -> float | None:
    """
    Calcula el Stop Loss basado en el swing low/high de las últimas
    config.HIGHEST_LOWEST_PERIODO velas (excluyendo la vela actual),
    reutilizando la misma lógica de niveles que el componente STRUCTURE
    de la estrategia, más un pequeño buffer en múltiplos de ATR.

    LONG:  SL = lowest_N  - (ATR × SL_BUFFER_ATR_MULT)
    SHORT: SL = highest_N + (ATR × SL_BUFFER_ATR_MULT)

    Requiere que df_5m tenga las columnas 'high', 'low', 'close' y 'ATR'
    ya calculadas. Devuelve None si no hay suficientes velas para tener
    un nivel válido (los primeros N valores del rolling son NaN).
    """
    periodo = config.HIGHEST_LOWEST_PERIODO
    niveles = calcular_niveles_estructura(df_5m, periodo=periodo)
    df = df_5m.join(niveles)

    if df.empty:
        return None

    ultima = df.iloc[-1]
    atr_actual = float(ultima["ATR"]) if "ATR" in df.columns and pd.notna(ultima["ATR"]) else 0.0
    buffer = atr_actual * config.SL_BUFFER_ATR_MULT

    col_lowest = f"lowest_{periodo}"
    col_highest = f"highest_{periodo}"

    if direccion == "LONG":
        nivel = ultima[col_lowest]
        if pd.isna(nivel):
            return None
        return float(nivel) - buffer

    elif direccion == "SHORT":
        nivel = ultima[col_highest]
        if pd.isna(nivel):
            return None
        return float(nivel) + buffer

    return None