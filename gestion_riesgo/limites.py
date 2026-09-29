import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import config
from gestion_riesgo.posiciones import OUTPUT_DIR_POSICIONES

logger = logging.getLogger(__name__)

MINUTOS_POR_DIA = 24 * 60


def contar_posiciones_abiertas() -> int:
    """
    Cuenta cuántas posiciones tienen estado 'abierta' entre TODOS los pares,
    leyendo los JSON de data/posiciones/. Los archivos con estado 'cerrada'
    (que se conservan en disco) no cuentan.

    Un archivo ilegible o corrupto se ignora con un aviso en el log, para que
    un fallo puntual no bloquee el análisis del resto de pares.
    """
    if not os.path.isdir(OUTPUT_DIR_POSICIONES):
        return 0

    total = 0
    for nombre in os.listdir(OUTPUT_DIR_POSICIONES):
        if not nombre.endswith(".json"):
            continue

        ruta = os.path.join(OUTPUT_DIR_POSICIONES, nombre)
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if datos.get("estado") == "abierta":
                total += 1
        except (OSError, json.JSONDecodeError, AttributeError) as e:
            logger.warning("No se pudo leer la posición %s: %s", ruta, e)

    return total


def _minuto_de_la_semana(dia: int, hora: int, minuto: int = 0) -> int:
    """Convierte (día de la semana, hora, minuto) en minutos desde el lunes 00:00."""
    return dia * MINUTOS_POR_DIA + hora * 60 + minuto


def esta_en_ventana_fin_de_semana(ahora: datetime | None = None) -> bool:
    """
    Devuelve True si 'ahora' cae dentro de la ventana sin señales nuevas
    (por defecto, viernes 20:00 -> domingo 07:00, hora de España).

    Se compara en 'minutos desde el lunes 00:00'. Si la ventana cruzara el
    domingo->lunes (inicio > fin), también se gestiona.

    'ahora' debe ser un datetime con zona horaria (aware); si es None se usa
    la hora actual. Existe como parámetro para poder probar la función con
    fechas concretas.
    """
    if not config.FILTRO_FIN_DE_SEMANA_ACTIVO:
        return False

    try:
        zona = ZoneInfo(config.ZONA_HORARIA_FILTRO)
    except ZoneInfoNotFoundError:
        # Sin base de datos de zonas (falta 'tzdata'): no bloqueamos, pero
        # lo dejamos bien visible en el log.
        logger.error(
            "Zona horaria '%s' no disponible (¿falta 'tzdata'?). "
            "Filtro de fin de semana DESACTIVADO en este ciclo.",
            config.ZONA_HORARIA_FILTRO,
        )
        return False

    ahora = ahora.astimezone(zona) if ahora else datetime.now(zona)

    actual = _minuto_de_la_semana(ahora.weekday(), ahora.hour, ahora.minute)
    inicio = _minuto_de_la_semana(config.FIN_SEMANA_INICIO_DIA, config.FIN_SEMANA_INICIO_HORA)
    fin = _minuto_de_la_semana(config.FIN_SEMANA_FIN_DIA, config.FIN_SEMANA_FIN_HORA)

    if inicio <= fin:
        return inicio <= actual < fin
    # Ventana que cruza el final de semana (domingo -> lunes)
    return actual >= inicio or actual < fin


def comprobar_limites_entrada(ahora: datetime | None = None) -> tuple[bool, str | None]:
    """
    Comprueba los límites de cartera/horario antes de abrir una posición nueva.

    Devuelve (permitido, motivo):
        (True, None)            -> se puede abrir
        (False, "<motivo>")     -> bloqueada; 'motivo' es un texto legible
    """
    if esta_en_ventana_fin_de_semana(ahora):
        return False, (
            f"filtro de fin de semana (vie {config.FIN_SEMANA_INICIO_HORA:02d}:00 "
            f"-> dom {config.FIN_SEMANA_FIN_HORA:02d}:00)"
        )

    abiertas = contar_posiciones_abiertas()
    if abiertas >= config.MAX_POSICIONES_SIMULTANEAS:
        return False, (
            f"máximo de posiciones simultáneas alcanzado "
            f"({abiertas}/{config.MAX_POSICIONES_SIMULTANEAS})"
        )

    return True, None