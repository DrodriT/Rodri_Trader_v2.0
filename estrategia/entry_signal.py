import pandas as pd

import config
from indicadores import calcular_volumen_sma

from .htf_filter import evaluar_htf_bias
from .mandatory_filter import cumple_mandatory_filter
from .structure import calcular_niveles_estructura, puntuar_structure
from .scoring import (
    puntuar_htf_bias,
    puntuar_trend,
    puntuar_rsi,
    puntuar_adx,
    puntuar_volume,
)


def _preparar_indicadores_5m(df_entrada: pd.DataFrame) -> pd.DataFrame:
    """
    Añade al DataFrame de 5m los indicadores derivados específicos de la
    estrategia (volumen SMA y niveles de estructura), que no forman parte
    de los indicadores 'generales' calculados en test_conexion_velas.py.

    Trabaja sobre una COPIA del DataFrame recibido, para no modificar el
    original que pueda seguir usando el script que llama a esta función.
    """
    df = df_entrada.copy()
    df["Volumen_SMA"] = calcular_volumen_sma(df, periodo=config.VOLUME_SMA_PERIODO)
    df = df.join(calcular_niveles_estructura(df, periodo=config.HIGHEST_LOWEST_PERIODO))
    return df


def _calcular_score_total(df_5m: pd.DataFrame, df_15m: pd.DataFrame, direccion: str) -> float:
    """Suma los 6 componentes del score para la última vela de df_5m."""
    return (
        puntuar_htf_bias(df_15m, direccion)
        + puntuar_trend(df_5m, direccion)
        + puntuar_rsi(df_5m, direccion)
        + puntuar_adx(df_5m)
        + puntuar_volume(df_5m)
        + puntuar_structure(df_5m, direccion)
    )


def generar_senal(par: str, df_5m: pd.DataFrame, df_15m: pd.DataFrame) -> dict:
    """
    Punto de entrada público de la estrategia (Algorithmic Entry Model V1.0).

    Orquesta, en orden:
        1. HTF Filter (15m)       -> descarta el par si es NEUTRAL
        2. Mandatory Filter (5m)  -> descarta el par si no cumple todas las condiciones
        3. Score (0-100)          -> calculado para la vela actual y la anterior
        4. Entry                  -> solo si el score CRUZA hacia arriba el umbral

    Requiere:
        df_5m con columnas:  'close','high','low','volume','EMA_rapida','EMA_lenta','RSI','ADX'
        df_15m con columnas: 'close','EMA_rapida','EMA_lenta'

    Devuelve un diccionario con el detalle completo de la evaluación, útil
    tanto para disparar la señal como para depurar/registrar por qué un par
    no entró.
    """
    resultado = {
        "par": par,
        "bias_htf": "NEUTRAL",
        "cumple_mandatory": False,
        "score_actual": 0.0,
        "score_anterior": 0.0,
        "senal": None,  # "LONG", "SHORT" o None
    }

    # ---------- 1) HTF Filter ----------
    bias = evaluar_htf_bias(df_15m)
    resultado["bias_htf"] = bias

    if bias == "NEUTRAL":
        return resultado  # No se sigue evaluando: sin tendencia clara en 15m

    # ---------- Preparación de indicadores derivados en 5m ----------
    df_5m_prep = _preparar_indicadores_5m(df_5m)

    # ---------- 2) Mandatory Filter ----------
    cumple = cumple_mandatory_filter(df_5m_prep, bias)
    resultado["cumple_mandatory"] = cumple

    if not cumple:
        return resultado  # No pasa el filtro obligatorio: no se calcula el score

    # ---------- 3) Score actual y anterior (para detectar el cruce) ----------
    score_actual = _calcular_score_total(df_5m_prep, df_15m, bias)

    if len(df_5m_prep) > 1:
        # Simulamos "como si la última vela no existiera todavía": recalculamos
        # el score usando el DataFrame sin la última fila, de forma que las
        # funciones de puntuación tomen automáticamente la vela anterior
        # como su 'última vela'.
        score_anterior = _calcular_score_total(df_5m_prep.iloc[:-1], df_15m, bias)
    else:
        score_anterior = 0.0

    resultado["score_actual"] = round(float(score_actual), 2)
    resultado["score_anterior"] = round(float(score_anterior), 2)

    # ---------- 4) Entry: cruce del umbral hacia arriba ----------
    if (
        score_actual >= config.SCORE_ENTRADA_MINIMO
        and score_anterior < config.SCORE_ENTRADA_MINIMO
    ):
        resultado["senal"] = bias

    return resultado