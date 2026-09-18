import json
import os
from datetime import datetime, timedelta, timezone

import config

# Carpeta donde se persiste el estado de cooldown de cada par, separada de
# data/posiciones/ (posición abierta/cerrada) y data/estadistica/ (histórico).
OUTPUT_DIR_COOLDOWN = os.path.join("data", "cooldown")


def _ruta_cooldown(par_base: str) -> str:
    """Construye (y crea si no existe) la ruta al JSON de cooldown de un par."""
    os.makedirs(OUTPUT_DIR_COOLDOWN, exist_ok=True)
    return os.path.join(OUTPUT_DIR_COOLDOWN, f"{par_base}.json")


def _leer_estado(par_base: str) -> dict:
    """Devuelve el último estado de cooldown guardado para el par, o {} si no hay."""
    ruta = _ruta_cooldown(par_base)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def registrar_cierre(par_base: str, motivo_cierre: str) -> None:
    """
    Se llama cada vez que se cierra una posición (motivo_cierre: 'SL', 'BE'
    o 'TP3') para actualizar el cooldown del par.

    Reglas:
        - Cierre por BE o TP3: cooldown de config.COOLDOWN_HORAS_NORMAL (4h)
          y se resetea el contador de SL consecutivos (la racha se rompe).
        - Cierre por SL: se incrementa el contador de SL consecutivos. Al
          alcanzar config.SL_CONSECUTIVOS_PARA_COOLDOWN_LARGO (2) SL
          seguidos, el cooldown de ESTE cierre sube a
          config.COOLDOWN_HORAS_SL_CONSECUTIVOS (12h).
    """
    estado_previo = _leer_estado(par_base)
    sl_consecutivos_previo = estado_previo.get("sl_consecutivos", 0)

    if motivo_cierre == "SL":
        sl_consecutivos = sl_consecutivos_previo + 1
    else:
        sl_consecutivos = 0  # BE o TP3 rompen la racha de SL seguidos

    horas_cooldown = (
        config.COOLDOWN_HORAS_SL_CONSECUTIVOS
        if sl_consecutivos >= config.SL_CONSECUTIVOS_PARA_COOLDOWN_LARGO
        else config.COOLDOWN_HORAS_NORMAL
    )

    ahora = datetime.now(timezone.utc)
    estado = {
        "motivo_cierre": motivo_cierre,
        "sl_consecutivos": sl_consecutivos,
        "cooldown_horas": horas_cooldown,
        "cooldown_hasta": (ahora + timedelta(hours=horas_cooldown)).isoformat(),
    }

    ruta = _ruta_cooldown(par_base)
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"  ❌ Error al guardar cooldown de {par_base}: {e}")


def en_cooldown(par_base: str) -> dict | None:
    """
    Comprueba si el par sigue en cooldown tras su último cierre.

    Devuelve None si NO hay cooldown activo (se puede evaluar una nueva
    señal con normalidad), o el dict de estado guardado por
    registrar_cierre() si el cooldown SIGUE activo (para poder informar
    del motivo y de cuándo termina).
    """
    estado = _leer_estado(par_base)
    if not estado:
        return None

    cooldown_hasta = datetime.fromisoformat(estado["cooldown_hasta"])
    ahora = datetime.now(timezone.utc)

    if ahora < cooldown_hasta:
        return estado
    return None