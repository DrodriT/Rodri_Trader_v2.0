import pandas as pd


def evaluar_htf_bias(df_htf: pd.DataFrame) -> str:
    """
    Evalúa el sesgo direccional (bias) en el timeframe superior (HTF, ej. 15m),
    usando la última vela disponible en df_htf.

    Reglas:
        LONG:    precio > EMA_lenta  Y  EMA_rapida > EMA_lenta
        SHORT:   precio < EMA_lenta  Y  EMA_rapida < EMA_lenta
        NEUTRAL: cualquier otro caso (no hay alineación clara de tendencia)

    Requiere que df_htf tenga ya calculadas las columnas:
        'close', 'EMA_rapida', 'EMA_lenta'
    """
    if df_htf.empty:
        return "NEUTRAL"

    ultima_vela = df_htf.iloc[-1]
    precio = ultima_vela["close"]
    ema_rapida = ultima_vela["EMA_rapida"]
    ema_lenta = ultima_vela["EMA_lenta"]

    if precio > ema_lenta and ema_rapida > ema_lenta:
        return "LONG"
    elif precio < ema_lenta and ema_rapida < ema_lenta:
        return "SHORT"
    else:
        return "NEUTRAL"