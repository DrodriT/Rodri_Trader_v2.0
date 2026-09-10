import pandas as pd

import config


def cumple_mandatory_filter(df_entrada: pd.DataFrame, bias_htf: str) -> bool:
    """
    Verifica el filtro obligatorio en el timeframe operativo (5m).
    Estas condiciones son eliminatorias: si no se cumplen TODAS, no se
    calcula ni se considera el score, independientemente de lo alto que
    pudiera salir.

    LONG (requiere bias_htf == "LONG"):
        precio > EMA_lenta
        EMA_rapida > EMA_lenta
        RSI > 50
        ADX >= ADX_MINIMO_MANDATORY

    SHORT (requiere bias_htf == "SHORT"): condiciones espejo.

    Requiere que df_entrada tenga ya calculadas las columnas:
        'close', 'EMA_rapida', 'EMA_lenta', 'RSI', 'ADX'
    """
    if bias_htf not in ("LONG", "SHORT"):
        return False

    if df_entrada.empty:
        return False

    ultima_vela = df_entrada.iloc[-1]
    precio = ultima_vela["close"]
    ema_rapida = ultima_vela["EMA_rapida"]
    ema_lenta = ultima_vela["EMA_lenta"]
    rsi = ultima_vela["RSI"]
    adx = ultima_vela["ADX"]

    # Filtro de fuerza de tendencia, común a LONG y SHORT
    if adx < config.ADX_MINIMO_MANDATORY:
        return False

    # IMPORTANTE: envolvemos el resultado en bool(...) porque las comparaciones
    # sobre valores de pandas (ultima_vela[...]) devuelven numpy.bool_, no el
    # bool nativo de Python. json.dump() no sabe serializar numpy.bool_ y
    # lanzaría TypeError al guardar el resultado.
    if bias_htf == "LONG":
        return bool(precio > ema_lenta and ema_rapida > ema_lenta and rsi > 50)
    else:  # bias_htf == "SHORT"
        return bool(precio < ema_lenta and ema_rapida < ema_lenta and rsi < 50)