
import json
import os
from datetime import datetime, timezone

# Archivo histórico de operaciones cerradas
OUTPUT_DIR_ESTADISTICA = os.path.join("data", "estadistica")
RUTA_OPERACIONES = os.path.join(
    OUTPUT_DIR_ESTADISTICA,
    "operaciones.json"
)


def _cargar_operaciones() -> list:
    """
    Carga el histórico de operaciones cerradas.
    Si no existe, devuelve una lista vacía.
    """
    try:
        with open(RUTA_OPERACIONES, "r", encoding="utf-8") as f:
            datos = json.load(f)

        return datos if isinstance(datos, list) else []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def registrar_operacion_cerrada(
    par: str,
    posicion: dict,
    motivo: str,
    precio_salida: float,
) -> None:
    """
    Registra una operación cerrada en data/estadistica/operaciones.json.

    Evita duplicar operaciones utilizando el id_operacion.
    """

    os.makedirs(OUTPUT_DIR_ESTADISTICA, exist_ok=True)

    operaciones = _cargar_operaciones()

    # Identificador único de la operación
    id_operacion = posicion["id_operacion"]

    # Evitar duplicados
    if any(
        op.get("id_operacion") == id_operacion
        for op in operaciones
    ):
        print(
            f"  ⚠️ Operación {id_operacion} "
            "ya registrada en estadísticas."
        )
        return

    timestamp_cierre = datetime.now(timezone.utc).isoformat()

    # Calcular duración
    timestamp_apertura = posicion["timestamp_apertura"]

    try:
        inicio = datetime.fromisoformat(timestamp_apertura)
        fin = datetime.fromisoformat(timestamp_cierre)

        duracion_segundos = int(
            (fin - inicio).total_seconds()
        )

    except (ValueError, TypeError):
        duracion_segundos = None

    # Resultado general de la operación
    if motivo in ("TP1", "TP2", "TP3"):
        resultado = "ganadora"
    elif motivo == "BE":
        resultado = "break_even"
    elif motivo == "SL":
        resultado = "perdedora"
    else:
        resultado = "desconocido"

    # Copia histórica de la posición
    operacion = {
        "id_operacion": id_operacion,

        "simbolo": par,
        "direccion": posicion["direccion"],

        "estado_final": "cerrada",
        "motivo_cierre": motivo,

        "precio_entrada": posicion["precio_entrada"],
        "precio_salida": precio_salida,

        "stop_loss_original": posicion["stop_loss_original"],
        "stop_loss_final": posicion["stop_loss_actual"],

        "tp1": posicion["tp1"],
        "tp2": posicion["tp2"],
        "tp3": posicion["tp3"],

        "tp1_alcanzado": posicion["tp1_alcanzado"],
        "tp2_alcanzado": posicion["tp2_alcanzado"],
        "tp3_alcanzado": posicion.get(
            "tp3_alcanzado",
            motivo == "TP3"
        ),

        "sl_movido_be": posicion["sl_movido_be"],

        "timestamp_apertura": timestamp_apertura,
        "timestamp_cierre": timestamp_cierre,

        "duracion_segundos": duracion_segundos,

        "resultado": resultado,
    }

    operaciones.append(operacion)

    try:
        with open(
            RUTA_OPERACIONES,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                operaciones,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"  📊 Operación {id_operacion} "
            f"registrada: {motivo}"
        )

    except Exception as e:
        print(
            f"  ❌ Error guardando estadísticas: {e}"
        )