"""
Paquete de gestión de riesgo: calcula Stop Loss, Take Profits (TP1/TP2/TP3)
y el apalancamiento/tamaño de posición sugeridos para una señal de entrada.

Expone una única función pública (calcular_gestion_riesgo) que orquesta
internamente los 3 sub-cálculos, siguiendo el mismo patrón que el paquete
'estrategia' (un único punto de entrada, detalles internos encapsulados).
"""

from .stop_loss import calcular_stop_loss
from .take_profit import calcular_take_profits
from .position_sizing import calcular_posicion

__all__ = ["calcular_gestion_riesgo"]


def calcular_gestion_riesgo(df_5m, precio_entrada: float, direccion: str) -> dict | None:
    """
    Calcula el plan de riesgo completo (SL, TP1/TP2/TP3, apalancamiento y
    tamaño de posición) para una señal de entrada ya confirmada.

    Devuelve None si la dirección no es válida o si no hay datos suficientes
    para calcular el SL (por ejemplo, menos de HIGHEST_LOWEST_PERIODO velas).
    """
    if direccion not in ("LONG", "SHORT"):
        return None

    sl = calcular_stop_loss(df_5m, direccion)
    if sl is None:
        return None

    tps = calcular_take_profits(df_5m, precio_entrada, sl, direccion)
    posicion = calcular_posicion(precio_entrada, sl)

    return {
        "direccion": direccion,
        "precio_entrada": round(float(precio_entrada), 6),
        "stop_loss": round(float(sl), 6),
        **tps,
        **posicion,
    }