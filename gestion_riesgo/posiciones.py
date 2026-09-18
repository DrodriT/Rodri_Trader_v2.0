import json
import os
from datetime import datetime, timezone
from gestion_riesgo.estadistica import registrar_operacion_cerrada
from gestion_riesgo.cooldown import registrar_cierre as registrar_cierre_cooldown

import pandas as pd

# Carpeta donde se persiste el ESTADO de las posiciones abiertas, separada de
# data/indicadores/ (que guarda snapshots de indicadores/estrategia). Un
# archivo por par que solo existe mientras la posición sigue 'abierta'.
OUTPUT_DIR_POSICIONES = os.path.join("data", "posiciones")


def _ruta_posicion(par_base: str) -> str:
    """Construye (y crea si no existe) la ruta al JSON de posición de un par."""
    os.makedirs(OUTPUT_DIR_POSICIONES, exist_ok=True)
    return os.path.join(OUTPUT_DIR_POSICIONES, f"{par_base}.json")


def cargar_posicion(par_base: str) -> dict | None:
    """
    Devuelve la posición ABIERTA de este par, o None si no hay ninguna
    (archivo inexistente, corrupto, o con estado 'cerrada').
    """
    ruta = _ruta_posicion(par_base)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if datos.get("estado") == "abierta":
            return datos
        return None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def guardar_posicion(par_base: str, posicion: dict) -> None:
    """Persiste el estado actual de la posición (abierta o recién cerrada)."""
    ruta = _ruta_posicion(par_base)
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(posicion, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"  ❌ Error al guardar posición de {par_base}: {e}")


def abrir_posicion(par_base: str, direccion: str, riesgo: dict, par: str | None = None,) -> dict:
    """
    Crea y persiste una nueva posición abierta a partir del plan de riesgo
    (SL/TP1/TP2/TP3) calculado por gestion_riesgo.calcular_gestion_riesgo().
    """
    timestamp_apertura = datetime.now(timezone.utc)
    posicion = {
        "id_operacion": (f"{par_base}_"f"{timestamp_apertura.strftime('%Y%m%d_%H%M%S_%f')}"),
        "simbolo": par if par is not None else par_base,
        "estado": "abierta",
        "direccion": direccion,
        "precio_entrada": riesgo["precio_entrada"],
        "stop_loss_original": riesgo["stop_loss"],
        "stop_loss_actual": riesgo["stop_loss"],
        "tp1": riesgo["tp1"],
        "tp2": riesgo["tp2"],
        "tp3": riesgo["tp3"],
        "tp1_alcanzado": False,
        "tp2_alcanzado": False,
        "tp3_alcanzado": False,
        "sl_movido_be": False,
        "timestamp_apertura": datetime.now(timezone.utc).isoformat(),
    }
    guardar_posicion(par_base, posicion)
    return posicion


def cerrar_posicion(par_base: str, posicion: dict, motivo: str, precio_salida: float, par: str,) -> None:
    """
    Marca la posición como cerrada (motivo: 'SL', 'BE' o 'TP3') y la persiste.
    A partir de este momento, cargar_posicion() volverá a devolver None para
    este par, liberándolo para que la estrategia pueda generar nuevas señales
    — sujeto al cooldown que se registra aquí mismo (ver gestion_riesgo/cooldown.py).
    """
    posicion["estado"] = "cerrada"
    posicion["motivo_cierre"] = motivo
    posicion["precio_salida"] = float(precio_salida)
    posicion["timestamp_cierre"] = datetime.now(timezone.utc).isoformat()

    # Persistir posición cerrada
    guardar_posicion(par_base, posicion)

    # Registramos la operación en estadísticas
    registrar_operacion_cerrada(
        par=par,
        posicion=posicion,
        motivo_cierre=motivo,
        precio_salida=float(precio_salida),
    )

    # Registramos el cooldown: 4h normal (BE/TP3), o 12h si van 2 SL seguidos.
    registrar_cierre_cooldown(par_base, motivo)


def evaluar_posicion(posicion: dict, ultima_vela: pd.Series) -> list[str]:
    """
    Compara el high/low de la última vela contra los niveles de la posición
    abierta y devuelve la lista de eventos ocurridos EN ESTE CICLO.

    Prioridad: si se toca el SL actual (que puede ya estar en breakeven),
    se devuelve solo ese evento y no se comprueban los TPs (la posición ya
    se cerró, no tiene sentido seguir evaluando objetivos).

    Eventos posibles: 'SL_TOCADO', 'BE_TOCADO', 'TP1_TOCADO', 'TP2_TOCADO',
    'TP3_TOCADO'. Puede devolver varios TPs a la vez si una vela muy grande
    los atraviesa todos de golpe.
    """
    eventos = []
    direccion = posicion["direccion"]
    high = float(ultima_vela["high"])
    low = float(ultima_vela["low"])
    sl_actual = posicion["stop_loss_actual"]

    if direccion == "LONG":
        if low <= sl_actual:
            eventos.append("BE_TOCADO" if posicion["sl_movido_be"] else "SL_TOCADO")
            return eventos

        if not posicion["tp1_alcanzado"] and high >= posicion["tp1"]:
            eventos.append("TP1_TOCADO")
        if not posicion["tp2_alcanzado"] and high >= posicion["tp2"]:
            eventos.append("TP2_TOCADO")
        if high >= posicion["tp3"]:
            eventos.append("TP3_TOCADO")

    elif direccion == "SHORT":
        if high >= sl_actual:
            eventos.append("BE_TOCADO" if posicion["sl_movido_be"] else "SL_TOCADO")
            return eventos

        if not posicion["tp1_alcanzado"] and low <= posicion["tp1"]:
            eventos.append("TP1_TOCADO")
        if not posicion["tp2_alcanzado"] and low <= posicion["tp2"]:
            eventos.append("TP2_TOCADO")
        if low <= posicion["tp3"]:
            eventos.append("TP3_TOCADO")

    return eventos