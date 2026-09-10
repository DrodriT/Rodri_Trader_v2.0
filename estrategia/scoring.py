import pandas as pd

import config

# ==============================================================================
# Bandas de puntuación intermedias del modelo V1.0.
# Los valores máximos de cada componente SÍ vienen de config.py (PUNTOS_*),
# pero las bandas intermedias son propias de esta versión del modelo y se
# documentan aquí para que quede claro de dónde salen.
# ==============================================================================

# --- HTF BIAS (máximo: config.PUNTOS_HTF_BIAS = 20) ---
HTF_BIAS_SPREAD_ALTO = 0.35   # % de separación EMA9/EMA21 respecto al precio
HTF_BIAS_SPREAD_MEDIO = 0.15
HTF_BIAS_PUNTOS_BAJO = 10.0
HTF_BIAS_PUNTOS_MEDIO = 15.0

# --- TREND (máximo: config.PUNTOS_TREND = 25) ---
TREND_SPREAD_ALTO = 0.25
TREND_SPREAD_MEDIO = 0.10
TREND_PUNTOS_BAJO = 12.0
TREND_PUNTOS_MEDIO = 18.0

# --- RSI (máximo: config.PUNTOS_RSI = 15) ---
RSI_PUNTOS_ZONA_SANA = 8.0     # 50-60 (LONG) / 40-50 (SHORT)
RSI_PUNTOS_ZONA_OPTIMA = 15.0  # 60-70 (LONG) / 30-40 (SHORT)
RSI_PUNTOS_EXTREMO = 10.0      # >70 (LONG) / <30 (SHORT) -> penaliza extremos

# --- ADX (máximo: config.PUNTOS_ADX = 15) ---
ADX_PUNTOS_INICIAL = 8.0    # 18-25
ADX_PUNTOS_OPTIMO = 15.0    # 25-35
ADX_PUNTOS_MADURO = 12.0    # >35 (tendencia ya muy avanzada)

# --- VOLUME (máximo: config.PUNTOS_VOLUME = 10) ---
VOLUME_RATIO_MEDIO = 1.0
VOLUME_RATIO_ALTO = 1.5
VOLUME_PUNTOS_MEDIO = 5.0


def puntuar_htf_bias(df_htf: pd.DataFrame, direccion: str) -> float:
    """Puntúa la fuerza de la tendencia en el HTF (15m) según separación de EMAs."""
    if direccion not in ("LONG", "SHORT") or df_htf.empty:
        return 0.0

    ultima = df_htf.iloc[-1]
    spread_pct = abs(ultima["EMA_rapida"] - ultima["EMA_lenta"]) / ultima["close"] * 100

    if spread_pct > HTF_BIAS_SPREAD_ALTO:
        return float(config.PUNTOS_HTF_BIAS)
    elif spread_pct > HTF_BIAS_SPREAD_MEDIO:
        return HTF_BIAS_PUNTOS_MEDIO
    else:
        return HTF_BIAS_PUNTOS_BAJO


def puntuar_trend(df_entrada: pd.DataFrame, direccion: str) -> float:
    """Puntúa la fuerza de la tendencia en el timeframe operativo (5m)."""
    if direccion not in ("LONG", "SHORT") or df_entrada.empty:
        return 0.0

    ultima = df_entrada.iloc[-1]
    spread_pct = abs(ultima["EMA_rapida"] - ultima["EMA_lenta"]) / ultima["close"] * 100

    if spread_pct > TREND_SPREAD_ALTO:
        return float(config.PUNTOS_TREND)
    elif spread_pct > TREND_SPREAD_MEDIO:
        return TREND_PUNTOS_MEDIO
    else:
        return TREND_PUNTOS_BAJO


def puntuar_rsi(df_entrada: pd.DataFrame, direccion: str) -> float:
    """Puntúa el RSI (5m) según su zona, en función de la dirección evaluada."""
    if direccion not in ("LONG", "SHORT") or df_entrada.empty:
        return 0.0

    rsi = df_entrada.iloc[-1]["RSI"]

    if direccion == "LONG":
        if rsi > 70:
            return RSI_PUNTOS_EXTREMO
        elif rsi > 60:
            return RSI_PUNTOS_ZONA_OPTIMA
        elif rsi > 50:
            return RSI_PUNTOS_ZONA_SANA
        return 0.0

    else:  # SHORT (espejo)
        if rsi < 30:
            return RSI_PUNTOS_EXTREMO
        elif rsi < 40:
            return RSI_PUNTOS_ZONA_OPTIMA
        elif rsi < 50:
            return RSI_PUNTOS_ZONA_SANA
        return 0.0


def puntuar_adx(df_entrada: pd.DataFrame) -> float:
    """Puntúa la fuerza de tendencia (ADX, 5m). No depende de la dirección."""
    if df_entrada.empty:
        return 0.0

    adx = df_entrada.iloc[-1]["ADX"]

    if adx > 35:
        return ADX_PUNTOS_MADURO
    elif adx > 25:
        return ADX_PUNTOS_OPTIMO
    elif adx >= config.ADX_MINIMO_MANDATORY:  # 18-25
        return ADX_PUNTOS_INICIAL
    return 0.0


def puntuar_volume(df_entrada: pd.DataFrame) -> float:
    """
    Puntúa el volumen relativo (5m): ratio entre el volumen actual y su SMA.
    Requiere que df_entrada tenga ya la columna 'Volumen_SMA'.
    """
    if df_entrada.empty:
        return 0.0

    ultima = df_entrada.iloc[-1]
    volumen_sma = ultima["Volumen_SMA"]

    if pd.isna(volumen_sma) or volumen_sma == 0:
        return 0.0

    ratio = ultima["volume"] / volumen_sma

    if ratio > VOLUME_RATIO_ALTO:
        return float(config.PUNTOS_VOLUME)
    elif ratio >= VOLUME_RATIO_MEDIO:
        return VOLUME_PUNTOS_MEDIO
    return 0.0