import config


def calcular_posicion(precio_entrada: float, sl: float) -> dict:
    """
    Calcula el apalancamiento sugerido y el tamaño de posición, de forma
    que si el precio llega al SL, la pérdida sea exactamente
    config.PCT_PERDIDA_MAXIMA_SL (%) del MARGEN asignado a esta operación
    (config.CAPITAL_POR_OPERACION_USDT), NO del capital total de la cuenta.

        distancia_SL_%   = |precio_entrada - SL| / precio_entrada × 100
        apalancamiento   = PCT_PERDIDA_MAXIMA_SL / distancia_SL_%
        tamaño_posición  = CAPITAL_POR_OPERACION_USDT × apalancamiento

    Ejemplo: con CAPITAL_POR_OPERACION_USDT = 100 y PCT_PERDIDA_MAXIMA_SL = 10,
    si el SL está a un 2% del precio de entrada -> apalancamiento = 5x ->
    si salta el SL, pierdes 10 USDT (el 10% de los 100 USDT de margen),
    sin importar cuál sea tu capital total en la cuenta.

    El apalancamiento se recorta a config.APALANCAMIENTO_MAXIMO si la
    fórmula pide más de eso (SL demasiado ajustado) — en ese caso, la
    pérdida real en el SL será MAYOR al % objetivo, y se marca con
    'apalancamiento_limitado': True para que lo tengas en cuenta.
    """
    distancia_pct = abs(precio_entrada - sl) / precio_entrada * 100

    if distancia_pct == 0:
        return {}

    apalancamiento_calculado = config.PCT_PERDIDA_MAXIMA_SL / distancia_pct
    apalancamiento_limitado = apalancamiento_calculado > config.APALANCAMIENTO_MAXIMO
    apalancamiento_final = min(apalancamiento_calculado, config.APALANCAMIENTO_MAXIMO)

    capital_entrada = config.CAPITAL_POR_OPERACION_USDT
    tamano_posicion_usdt = capital_entrada * apalancamiento_final
    cantidad_activo = tamano_posicion_usdt / precio_entrada

    # Si el apalancamiento se recortó, la pérdida real en el SL ya no es
    # PCT_PERDIDA_MAXIMA_SL, sino esta cifra recalculada con el apalancamiento limitado.
    perdida_real_pct_margen = (
        round(apalancamiento_final * distancia_pct, 2) if apalancamiento_limitado else config.PCT_PERDIDA_MAXIMA_SL
    )
    perdida_real_usdt = round(capital_entrada * perdida_real_pct_margen / 100, 2)

    return {
        "distancia_sl_pct": round(distancia_pct, 3),
        "apalancamiento_sugerido": round(apalancamiento_final, 2),
        "apalancamiento_limitado": apalancamiento_limitado,
        "perdida_estimada_pct_margen": perdida_real_pct_margen,
        "perdida_estimada_usdt": perdida_real_usdt,
        "capital_entrada_usdt": round(capital_entrada, 2),
        "tamano_posicion_usdt": round(tamano_posicion_usdt, 2),
        "cantidad_activo": round(cantidad_activo, 6),
    }