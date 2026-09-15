import pandas as pd

import config
from estrategia.structure import calcular_niveles_estructura


def calcular_take_profits(
    df_5m: pd.DataFrame, precio_entrada: float, sl: float, direccion: str
) -> dict:
    """
    Calcula TP1, TP2 y TP3 como múltiplos de Riesgo:Beneficio sobre la
    distancia al SL (config.RR_TP1/2/3), y los valida contra el próximo
    nivel de estructura visible (swing high/low reciente):

        - Si el TP queda ANTES de alcanzar ese nivel -> validado (más realista).
        - Si el TP queda MÁS ALLÁ de ese nivel -> no validado (el precio
          tendría que romper una resistencia/soporte visible para llegar).

    La validación es informativa, NO recorta ni modifica los TPs
    calculados por R:R: solo te avisa de cuáles son más exigentes.
    """
    riesgo = abs(precio_entrada - sl)
    periodo = config.HIGHEST_LOWEST_PERIODO

    niveles = calcular_niveles_estructura(df_5m, periodo=periodo)
    df = df_5m.join(niveles)
    ultima = df.iloc[-1]

    if direccion == "LONG":
        tp1 = precio_entrada + riesgo * config.RR_TP1
        tp2 = precio_entrada + riesgo * config.RR_TP2
        tp3 = precio_entrada + riesgo * config.RR_TP3
        nivel_estructura = ultima.get(f"highest_{periodo}")  # próxima resistencia visible
    elif direccion == "SHORT":
        tp1 = precio_entrada - riesgo * config.RR_TP1
        tp2 = precio_entrada - riesgo * config.RR_TP2
        tp3 = precio_entrada - riesgo * config.RR_TP3
        nivel_estructura = ultima.get(f"lowest_{periodo}")  # próximo soporte visible
    else:
        return {}

    nivel_estructura = float(nivel_estructura) if pd.notna(nivel_estructura) else None

    def _validar(tp: float) -> bool | None:
        if nivel_estructura is None:
            return None  # sin datos suficientes para validar
        if direccion == "LONG":
            return tp <= nivel_estructura
        return tp >= nivel_estructura

    return {
        "tp1": round(float(tp1), 6),
        "tp2": round(float(tp2), 6),
        "tp3": round(float(tp3), 6),
        "nivel_estructura_referencia": round(nivel_estructura, 6) if nivel_estructura is not None else None,
        "tp1_validado_por_estructura": _validar(tp1),
        "tp2_validado_por_estructura": _validar(tp2),
        "tp3_validado_por_estructura": _validar(tp3),
    }