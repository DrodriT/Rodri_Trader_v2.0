import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config

# Histórico de operaciones cerradas (lo escribe gestion_riesgo/estadistica.py)
ARCHIVO_OPERACIONES = os.path.join("data", "estadistica", "operaciones.json")
# Una posición por par mientras está abierta (lo escribe gestion_riesgo/posiciones.py)
CARPETA_POSICIONES = os.path.join("data", "posiciones")


# ==============================================================================
# TIEMPO
# ==============================================================================
def zona_horaria() -> ZoneInfo:
    """Zona horaria que define cuándo empieza y acaba el 'día' y la 'semana'."""
    return ZoneInfo(config.ZONA_HORARIA_INFORMES)


def ahora_local() -> datetime:
    """Fecha y hora actuales en la zona horaria de los informes."""
    return datetime.now(zona_horaria())


def rango_dia(ahora: datetime) -> tuple[datetime, datetime]:
    """Devuelve (inicio, fin) del día local de 'ahora': de 00:00 a 00:00 del día siguiente."""
    inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    return inicio, inicio + timedelta(days=1)


def rango_semana(ahora: datetime) -> tuple[datetime, datetime]:
    """Devuelve (inicio, fin) de la semana local de 'ahora': de lunes 00:00 a lunes 00:00."""
    inicio_dia, _ = rango_dia(ahora)
    inicio = inicio_dia - timedelta(days=ahora.weekday())
    return inicio, inicio + timedelta(days=7)


def formatear_duracion(duracion: timedelta) -> str:
    """Formatea una duración de forma compacta: '2d 3h', '4h 10m' o '25m'."""
    minutos_totales = max(int(duracion.total_seconds() // 60), 0)
    dias, resto = divmod(minutos_totales, 1440)
    horas, minutos = divmod(resto, 60)
    if dias:
        return f"{dias}d {horas}h"
    if horas:
        return f"{horas}h {minutos}m"
    return f"{minutos}m"


def calcular_duracion(op: dict) -> timedelta | None:
    """Duración entre apertura y cierre de una operación (o None si faltan datos)."""
    try:
        apertura = datetime.fromisoformat(op["timestamp_apertura"])
        cierre = datetime.fromisoformat(op["timestamp_cierre"])
        return cierre - apertura
    except (KeyError, TypeError, ValueError):
        return None


# ==============================================================================
# PNL
# ==============================================================================
def calcular_pnl_operacion(op: dict) -> float:
    """
    Calcula el PnL en USDT de una operación cerrada, reproduciendo la misma
    fórmula que gestion_riesgo/position_sizing.py usó para dimensionarla:

        apalancamiento = PCT_PERDIDA_MAXIMA_SL / distancia al SL original (%)
                         (recortado a APALANCAMIENTO_MAXIMO)
        tamaño posición = CAPITAL_POR_OPERACION_USDT x apalancamiento
        PnL = tamaño posición x variación del precio (con signo según LONG/SHORT)

    Modelo simple: se asume que TODA la posición se cierra al precio_salida
    registrado (sin cierres parciales en TP1/TP2). Sirve tanto para las
    operaciones de operaciones.json como para el dict de una posición recién
    cerrada, porque ambos comparten estas claves.
    """
    entrada = op.get("precio_entrada")
    salida = op.get("precio_salida")
    sl_original = op.get("stop_loss_original")
    if not entrada or salida is None or sl_original is None:
        return 0.0

    distancia_sl_pct = abs(entrada - sl_original) / entrada * 100
    if distancia_sl_pct == 0:
        return 0.0

    apalancamiento = min(
        config.PCT_PERDIDA_MAXIMA_SL / distancia_sl_pct,
        config.APALANCAMIENTO_MAXIMO,
    )
    tamano_posicion = config.CAPITAL_POR_OPERACION_USDT * apalancamiento

    variacion = (salida - entrada) / entrada
    if op.get("direccion") == "SHORT":
        variacion = -variacion  # en corto se gana cuando el precio baja

    return tamano_posicion * variacion


# ==============================================================================
# CARGA DE DATOS
# ==============================================================================
def cargar_operaciones() -> list[dict]:
    """
    Carga las operaciones cerradas y añade a cada una: pnl_usdt, cierre y
    apertura (datetimes en zona local), duracion y par_base. Devuelve la lista
    ordenada por fecha de cierre. Ignora las entradas con fechas ilegibles.
    """
    try:
        with open(ARCHIVO_OPERACIONES, "r", encoding="utf-8") as f:
            crudas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    if not isinstance(crudas, list):
        return []

    zona = zona_horaria()
    operaciones = []
    for op in crudas:
        try:
            cierre = datetime.fromisoformat(op["timestamp_cierre"]).astimezone(zona)
            apertura = datetime.fromisoformat(op["timestamp_apertura"]).astimezone(zona)
        except (KeyError, TypeError, ValueError):
            continue

        enriquecida = dict(op)
        enriquecida.update(
            {
                "pnl_usdt": calcular_pnl_operacion(op),
                "cierre": cierre,
                "apertura": apertura,
                "duracion": cierre - apertura,
                "par_base": str(op.get("par", "?")).split("/")[0],
            }
        )
        operaciones.append(enriquecida)

    operaciones.sort(key=lambda o: o["cierre"])
    return operaciones


def cargar_posiciones_abiertas() -> list[dict]:
    """Devuelve las posiciones actualmente abiertas (una por par como máximo)."""
    if not os.path.isdir(CARPETA_POSICIONES):
        return []

    abiertas = []
    for nombre in sorted(os.listdir(CARPETA_POSICIONES)):
        if not nombre.endswith(".json"):
            continue
        try:
            with open(os.path.join(CARPETA_POSICIONES, nombre), "r", encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if datos.get("estado") == "abierta":
            abiertas.append(datos)
    return abiertas


def filtrar_periodo(operaciones: list[dict], inicio: datetime, fin: datetime) -> list[dict]:
    """Operaciones cerradas dentro de [inicio, fin)."""
    return [o for o in operaciones if inicio <= o["cierre"] < fin]


def pnl_del_dia(ahora: datetime | None = None) -> tuple[float, int]:
    """Devuelve (PnL acumulado, nº de operaciones cerradas) del día local en curso."""
    ahora = ahora or ahora_local()
    inicio, fin = rango_dia(ahora)
    ops = filtrar_periodo(cargar_operaciones(), inicio, fin)
    return sum(o["pnl_usdt"] for o in ops), len(ops)


# ==============================================================================
# MÉTRICAS
# ==============================================================================
def resumir(ops: list[dict]) -> dict:
    """
    Métricas básicas de un conjunto de operaciones. El winrate se calcula
    sobre las operaciones decididas (TP3 vs SL), sin contar los BE. El
    profit factor es beneficio bruto / pérdida bruta según el signo del PnL.
    """
    ganadas = [o for o in ops if o["resultado"] == "GANANCIA"]
    perdidas = [o for o in ops if o["resultado"] == "PERDIDA"]
    be = [o for o in ops if o["resultado"] == "BREAKEVEN"]

    pnl_total = sum(o["pnl_usdt"] for o in ops)
    beneficio_bruto = sum(o["pnl_usdt"] for o in ops if o["pnl_usdt"] > 0)
    perdida_bruta = -sum(o["pnl_usdt"] for o in ops if o["pnl_usdt"] < 0)
    decididas = len(ganadas) + len(perdidas)

    if perdida_bruta > 0:
        profit_factor = beneficio_bruto / perdida_bruta
    else:
        profit_factor = float("inf") if beneficio_bruto > 0 else None

    return {
        "n": len(ops),
        "ganadas": len(ganadas),
        "perdidas": len(perdidas),
        "be": len(be),
        "pnl": pnl_total,
        "winrate": (len(ganadas) / decididas * 100) if decididas else None,
        "profit_factor": profit_factor,
        "pnl_medio": (pnl_total / len(ops)) if ops else None,
        "mejor": max(ops, key=lambda o: o["pnl_usdt"]) if ops else None,
        "peor": min(ops, key=lambda o: o["pnl_usdt"]) if ops else None,
    }


def embudo_objetivos(ops: list[dict]) -> dict | None:
    """Qué porcentaje de las operaciones llegó a TP1, TP2 y TP3."""
    if not ops:
        return None
    n = len(ops)
    tp1 = sum(1 for o in ops if o.get("tp1_alcanzado"))
    tp2 = sum(1 for o in ops if o.get("tp2_alcanzado"))
    tp3 = sum(1 for o in ops if o.get("tp3_alcanzado"))
    return {
        "n": n,
        "tp1": tp1, "tp1_pct": tp1 / n * 100,
        "tp2": tp2, "tp2_pct": tp2 / n * 100,
        "tp3": tp3, "tp3_pct": tp3 / n * 100,
    }


def max_drawdown(ops: list[dict]) -> float:
    """Mayor caída (en USDT) desde un máximo de PnL acumulado dentro del periodo."""
    acumulado = pico = caida_max = 0.0
    for o in ops:
        acumulado += o["pnl_usdt"]
        pico = max(pico, acumulado)
        caida_max = max(caida_max, pico - acumulado)
    return caida_max


def rachas(ops: list[dict]) -> tuple[int, int]:
    """
    Devuelve (racha máxima de TP3 seguidos, racha máxima de SL seguidos).
    Un BE corta ambas rachas.
    """
    mejor_gan = mejor_per = act_gan = act_per = 0
    for o in ops:
        if o["resultado"] == "GANANCIA":
            act_gan, act_per = act_gan + 1, 0
        elif o["resultado"] == "PERDIDA":
            act_gan, act_per = 0, act_per + 1
        else:
            act_gan = act_per = 0
        mejor_gan = max(mejor_gan, act_gan)
        mejor_per = max(mejor_per, act_per)
    return mejor_gan, mejor_per


def duracion_media(ops: list[dict]) -> timedelta | None:
    """Duración media de un conjunto de operaciones."""
    if not ops:
        return None
    return sum((o["duracion"] for o in ops), timedelta()) / len(ops)


def agrupar_por_par(ops: list[dict]) -> list[dict]:
    """Métricas por par, ordenadas de mayor a menor PnL."""
    grupos: dict[str, list[dict]] = {}
    for o in ops:
        grupos.setdefault(o["par_base"], []).append(o)

    filas = [{"par": par, **resumir(lista)} for par, lista in grupos.items()]
    filas.sort(key=lambda f: f["pnl"], reverse=True)
    return filas


def agrupar_por_direccion(ops: list[dict]) -> dict[str, dict]:
    """Métricas separadas para LONG y SHORT."""
    return {
        direccion: resumir([o for o in ops if o.get("direccion") == direccion])
        for direccion in ("LONG", "SHORT")
    }


def agrupar_por_dia(ops: list[dict], inicio: datetime, dias: int = 7) -> list[dict]:
    """Nº de operaciones y PnL de cada uno de los 'dias' días desde 'inicio'."""
    filas = []
    for i in range(dias):
        dia_ini = inicio + timedelta(days=i)
        lista = filtrar_periodo(ops, dia_ini, dia_ini + timedelta(days=1))
        filas.append(
            {"fecha": dia_ini, "n": len(lista), "pnl": sum(o["pnl_usdt"] for o in lista)}
        )
    return filas


def curva_capital(ops: list[dict]) -> list[float]:
    """Capital tras cada operación cerrada, empezando en CAPITAL_TOTAL_USDT."""
    capital = config.CAPITAL_TOTAL_USDT
    curva = [capital]
    for o in ops:
        capital += o["pnl_usdt"]
        curva.append(capital)
    return curva