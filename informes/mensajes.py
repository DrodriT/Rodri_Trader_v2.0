from datetime import datetime, timedelta

import config

from .calculo import (
    agrupar_por_dia,
    agrupar_por_direccion,
    agrupar_por_par,
    ahora_local,
    cargar_operaciones,
    cargar_posiciones_abiertas,
    curva_capital,
    duracion_media,
    embudo_objetivos,
    filtrar_periodo,
    formatear_duracion,
    max_drawdown,
    rachas,
    rango_dia,
    rango_semana,
    resumir,
)

# Nombres de día en español (se evita depender del idioma del sistema).
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
ICONO_RESULTADO = {"GANANCIA": "✅", "PERDIDA": "❌", "BREAKEVEN": "⚖️"}
ICONO_DIRECCION = {"LONG": "🟢", "SHORT": "🔴"}

# Máximo de filas en las listas largas, para que el mensaje siga siendo legible.
MAX_DETALLE_DIARIO = 15
MAX_RANKING = 5


# ==============================================================================
# FORMATO
# ==============================================================================
def _pnl(valor: float | None) -> str:
    """Formatea un PnL con signo; los valores casi nulos salen como +0.00, no -0.00."""
    if valor is None:
        return "N/D"
    if abs(valor) < 0.005:
        valor = 0.0
    return f"{valor:+.2f}"


def _texto_ops(n: int) -> str:
    """'1 op' / '3 ops'."""
    return f"{n} op" if n == 1 else f"{n} ops"


def _porcentaje(valor: float | None) -> str:
    return f"{valor:.1f}%" if valor is not None else "N/D"


def _profit_factor(valor: float | None) -> str:
    if valor is None:
        return "N/D"
    if valor == float("inf"):
        return "∞"
    return f"{valor:.2f}"


def _linea_conteo(r: dict) -> str:
    """Ej.: 'Operaciones: 5 | ✅ 2 TP3 | ❌ 1 SL | ⚖️ 2 BE'."""
    return (
        f"Operaciones: {r['n']} | ✅ {r['ganadas']} TP3 | "
        f"❌ {r['perdidas']} SL | ⚖️ {r['be']} BE"
    )


def _fecha_corta(fecha: datetime) -> str:
    return fecha.strftime("%d/%m")


def _texto_operacion(o: dict) -> str:
    """Una línea de detalle: icono, par, dirección, PnL y duración."""
    icono = ICONO_RESULTADO.get(o["resultado"], "•")
    return (
        f"{icono} {o['par_base']} {o['direccion']} "
        f"{_pnl(o['pnl_usdt'])} ({formatear_duracion(o['duracion'])})"
    )


def _texto_extremo(o: dict | None) -> str:
    return f"{o['par_base']} {o['direccion']} {_pnl(o['pnl_usdt'])}" if o else "N/D"


def _bloque_balance_total(todas: list[dict]) -> str:
    """Capital actual y retorno desde el inicio del test."""
    capital_inicial = config.CAPITAL_TOTAL_USDT
    capital_actual = curva_capital(todas)[-1]
    retorno = (capital_actual - capital_inicial) / capital_inicial * 100
    r = resumir(todas)
    return (
        f"Operaciones cerradas: {r['n']} | PnL total: {_pnl(r['pnl'])} USDT\n"
        f"Capital: {capital_inicial:,.2f} → {capital_actual:,.2f} USDT ({retorno:+.2f}%)"
    )


# ==============================================================================
# INFORME DIARIO
# ==============================================================================
def construir_informe_diario(ahora: datetime | None = None) -> str:
    """
    Informe de fin de día: resumen de las operaciones cerradas hoy (zona
    local), detalle de cada una, posiciones que siguen abiertas y balance
    total desde el inicio del test.
    """
    ahora = ahora or ahora_local()
    inicio, fin = rango_dia(ahora)
    todas = cargar_operaciones()
    ops = filtrar_periodo(todas, inicio, fin)
    r = resumir(ops)
    abiertas = cargar_posiciones_abiertas()

    lineas = [f"📅 *Informe diario* — {ahora.strftime('%d/%m/%Y')}", ""]

    # ---- Cierres del día ----
    lineas.append("*Cierres de hoy*")
    if not ops:
        lineas.append("Sin operaciones cerradas hoy.")
    else:
        lineas.append(_linea_conteo(r))
        lineas.append(f"PnL del día: {_pnl(r['pnl'])} USDT")
        lineas.append(
            f"Winrate (sin BE): {_porcentaje(r['winrate'])} | "
            f"Profit factor: {_profit_factor(r['profit_factor'])}"
        )
        lineas.append(f"Mejor: {_texto_extremo(r['mejor'])} | Peor: {_texto_extremo(r['peor'])}")

        lineas += ["", "*Detalle*"]
        for o in ops[:MAX_DETALLE_DIARIO]:
            lineas.append(_texto_operacion(o))
        if len(ops) > MAX_DETALLE_DIARIO:
            lineas.append(f"… y {len(ops) - MAX_DETALLE_DIARIO} más")

    # ---- Posiciones abiertas ----
    lineas += ["", f"*Posiciones abiertas ({len(abiertas)})*"]
    if not abiertas:
        lineas.append("Ninguna.")
    for p in abiertas:
        par = str(p.get("simbolo", "?")).split("/")[0]
        icono = ICONO_DIRECCION.get(p.get("direccion"), "•")
        objetivos = [f"TP{i}✅" for i in (1, 2) if p.get(f"tp{i}_alcanzado")]
        estado_tp = " ".join(objetivos) if objetivos else "sin TP"
        lineas.append(
            f"{icono} {par} {p.get('direccion')} | Entrada {p.get('precio_entrada', 0):,.4f} | "
            f"SL {p.get('stop_loss_actual', 0):,.4f} | {estado_tp}"
        )

    # ---- Señales abiertas hoy ----
    abiertas_hoy = sum(1 for o in todas if inicio <= o["apertura"] < fin)
    for p in abiertas:
        try:
            apertura = datetime.fromisoformat(p["timestamp_apertura"]).astimezone(ahora.tzinfo)
        except (KeyError, TypeError, ValueError):
            continue
        if inicio <= apertura < fin:
            abiertas_hoy += 1
    lineas += ["", f"Señales abiertas hoy: {abiertas_hoy}"]

    # ---- Balance total ----
    lineas += ["", "*Balance total*", _bloque_balance_total(todas)]

    return "\n".join(lineas)


# ==============================================================================
# INFORME SEMANAL
# ==============================================================================
def construir_informe_semanal(ahora: datetime | None = None) -> str:
    """
    Informe completo de la semana (lunes a domingo, zona local): resumen,
    embudo de objetivos (cuántas operaciones llegan a TP1/TP2/TP3), LONG vs
    SHORT, PnL por día, ranking de pares, extremos y rachas, comparativa con
    la semana anterior y balance total desde el inicio del test.
    """
    ahora = ahora or ahora_local()
    inicio, fin = rango_semana(ahora)
    todas = cargar_operaciones()
    ops = filtrar_periodo(todas, inicio, fin)
    r = resumir(ops)

    ultimo_dia = fin - timedelta(days=1)
    lineas = [
        f"📊 *Informe semanal* — {_fecha_corta(inicio)} al {ultimo_dia.strftime('%d/%m/%Y')}",
        "",
    ]

    if not ops:
        lineas.append("Sin operaciones cerradas esta semana.")
    else:
        # ---- Resumen ----
        dur = duracion_media(ops)
        lineas += [
            "*Resumen de la semana*",
            _linea_conteo(r),
            f"PnL: {_pnl(r['pnl'])} USDT | Media por operación: {_pnl(r['pnl_medio'])}",
            f"Winrate (sin BE): {_porcentaje(r['winrate'])} | "
            f"Profit factor: {_profit_factor(r['profit_factor'])}",
            f"Drawdown máximo: -{max_drawdown(ops):.2f} USDT",
            f"Duración media: {formatear_duracion(dur) if dur else 'N/D'}",
            "",
        ]

        # ---- Embudo de objetivos ----
        e = embudo_objetivos(ops)
        lineas += [
            "*Embudo de objetivos*",
            f"TP1 alcanzado: {e['tp1_pct']:.0f}% ({e['tp1']}/{e['n']})",
            f"TP2 alcanzado: {e['tp2_pct']:.0f}% ({e['tp2']}/{e['n']})",
            f"TP3 alcanzado: {e['tp3_pct']:.0f}% ({e['tp3']}/{e['n']})",
            f"SL directo (sin llegar a TP1): {r['perdidas']} ({r['perdidas'] / r['n'] * 100:.0f}%)",
            "",
        ]

        # ---- Por dirección ----
        lineas.append("*Por dirección*")
        for direccion, rd in agrupar_por_direccion(ops).items():
            if rd["n"]:
                lineas.append(
                    f"{ICONO_DIRECCION[direccion]} {direccion}: {rd['n']} ops | "
                    f"{_pnl(rd['pnl'])} USDT | winrate {_porcentaje(rd['winrate'])}"
                )
            else:
                lineas.append(f"{ICONO_DIRECCION[direccion]} {direccion}: sin operaciones")
        lineas.append("")

        # ---- Por día ----
        lineas.append("*Por día*")
        for fila in agrupar_por_dia(ops, inicio):
            nombre = DIAS_SEMANA[fila["fecha"].weekday()]
            lineas.append(
                f"{nombre} {_fecha_corta(fila['fecha'])}: {fila['n']} ops | {_pnl(fila['pnl'])}"
            )
        lineas.append("")

        # ---- Ranking de pares ----
        pares = agrupar_por_par(ops)
        mejores = [p for p in pares if p["pnl"] > 0][:MAX_RANKING]
        peores = sorted((p for p in pares if p["pnl"] < 0), key=lambda p: p["pnl"])[:MAX_RANKING]
        lineas.append("*Ranking de pares*")
        if not mejores and not peores:
            lineas.append("Sin pares con resultado positivo ni negativo.")
        for p in mejores:
            lineas.append(f"🟢 {p['par']}: {_pnl(p['pnl'])} ({_texto_ops(p['n'])})")
        for p in peores:
            lineas.append(f"🔴 {p['par']}: {_pnl(p['pnl'])} ({_texto_ops(p['n'])})")
        lineas.append("")

        # ---- Extremos y rachas ----
        racha_tp3, racha_sl = rachas(ops)
        lineas += [
            "*Extremos y rachas*",
            f"Mejor operación: {_texto_extremo(r['mejor'])}",
            f"Peor operación: {_texto_extremo(r['peor'])}",
            f"Racha máx. de TP3 seguidos: {racha_tp3} | de SL seguidos: {racha_sl}",
            "",
        ]

    # ---- Comparativa con la semana anterior ----
    ini_prev, fin_prev = inicio - timedelta(days=7), inicio
    ops_prev = filtrar_periodo(todas, ini_prev, fin_prev)
    lineas.append("*Comparativa con la semana anterior*")
    if not ops_prev:
        lineas.append("Sin operaciones la semana anterior.")
    else:
        rp = resumir(ops_prev)
        lineas += [
            f"PnL: {_pnl(r['pnl'])} vs {_pnl(rp['pnl'])} (diferencia {_pnl(r['pnl'] - rp['pnl'])})",
            f"Operaciones: {r['n']} vs {rp['n']} | "
            f"Winrate: {_porcentaje(r['winrate'])} vs {_porcentaje(rp['winrate'])}",
        ]

    # ---- Balance total ----
    lineas += ["", "*Acumulado desde el inicio del test*", _bloque_balance_total(todas)]

    return "\n".join(lineas)