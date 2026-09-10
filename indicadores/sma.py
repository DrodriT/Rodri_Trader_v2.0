import pandas as pd


# ==============================================================================
# SMA DE PRECIO
# ==============================================================================
def calcular_sma(
    df: pd.DataFrame, periodo: int = 20, columna: str = "close"
) -> pd.Series:
    """Media Móvil Simple: promedio aritmético de los últimos N cierres."""
    return df[columna].rolling(window=periodo).mean()


# ==============================================================================
# SMA DE VOLUMEN
# ==============================================================================
# Se separa de calcular_sma porque, aunque la operación matemática es la misma
# (media móvil simple), conceptualmente actúa sobre una columna distinta
# ('volume' en vez de 'close') y se usa para un propósito distinto dentro
# del modelo de scoring: medir si el volumen actual está por encima o por
# debajo de su media reciente (componente VOLUME del score de estrategia).
def calcular_volumen_sma(df: pd.DataFrame, periodo: int = 20) -> pd.Series:
    """
    Media Móvil Simple del VOLUMEN: promedio de las últimas N velas de volumen.

    Se usa como referencia para detectar picos de actividad: comparando el
    volumen de la vela actual contra esta media (ratio = volumen_actual / SMA),
    un ratio > 1 indica actividad por encima de lo habitual.
    """
    return df["volume"].rolling(window=periodo).mean()