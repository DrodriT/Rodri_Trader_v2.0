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


def generar_senal(
    par: str,
    df_5m: pd.DataFrame,
    df_15m: pd.DataFrame,
    resultado_previo: dict | None = None,
) -> dict:
    """
    Punto de entrada público de la estrategia (Algorithmic Entry Model V1.0).

    Orquesta, en orden:
        1. HTF Filter (15m)       -> descarta el par si es NEUTRAL
        2. Mandatory Filter (5m)  -> descarta el par si no cumple todas las condiciones
        3. Score (0-100)          -> calculado para la vela actual
        4. Entry                  -> solo si el score CRUZA hacia arriba el umbral,
                                      comparado contra la ÚLTIMA EJECUCIÓN REAL
                                      (no contra la vela anterior del mismo lote)

    Parámetros:
        df_5m, df_15m: DataFrames con los indicadores ya calculados.
        resultado_previo: bloque 'estrategia' guardado en la ejecución anterior
            para este mismo par (leído de su JSON persistido), o None si no
            existe (primera ejecución para este par). Debe contener al menos
            'bias_htf' y 'score_actual' para poder usarse como referencia.

    Requiere:
        df_5m con columnas:  'close','high','low','volume','EMA_rapida','EMA_lenta','RSI','ADX'
        df_15m con columnas: 'close','EMA_rapida','EMA_lenta'

    IMPORTANTE: esta función SIEMPRE termina en un 'return resultado' explícito,
    en cualquier rama posible (NEUTRAL, Mandatory Filter no cumplido, o flujo
    completo). Esto es deliberado: una función que "cae" al final sin return
    explícito devuelve None de forma implícita en Python, lo que rompería a
    quien la llama (ej. test_conexion_velas.py hace .pop() sobre el resultado).
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

    # ---------- 3) Score actual ----------
    score_actual = _calcular_score_total(df_5m_prep, df_15m, bias)
    resultado["score_actual"] = round(float(score_actual), 2)

    # ---------- Score anterior: referencia REAL de la última ejecución ----------
    # Solo es comparable si la ejecución anterior evaluó la MISMA dirección
    # (bias_htf); si el sesgo cambió (ej. de SHORT a LONG) o no hay ejecución
    # previa para este par, no existe una referencia real -> partimos de 0.0.
    if (
        resultado_previo is not None
        and resultado_previo.get("bias_htf") == bias
        and resultado_previo.get("score_actual") is not None
    ):
        score_anterior = float(resultado_previo["score_actual"])
    else:
        score_anterior = 0.0

    resultado["score_anterior"] = round(score_anterior, 2)

    # ---------- 4) Entry: cruce del umbral hacia arriba ----------
    if (
        score_actual >= config.SCORE_ENTRADA_MINIMO
        and score_anterior < config.SCORE_ENTRADA_MINIMO
    ):
        resultado["senal"] = bias

    return resultado