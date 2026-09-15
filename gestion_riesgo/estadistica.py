import json
import os
from datetime import datetime, timezone


OUTPUT_DIR_ESTADISTICA = os.path.join("data", "estadistica")
ARCHIVO_ESTADISTICA = os.path.join(
    OUTPUT_DIR_ESTADISTICA,
    "operaciones.json",
)


def registrar_operacion_cerrada(
    par: str,
    posicion: dict,
    motivo_cierre: str,
    precio_salida: float,
) -> None:
    """
    Registra una operación cerrada en data/estadistica/operaciones.json.

    La operación se añade al histórico sin sobrescribir las operaciones
    anteriores.
    """

    os.makedirs(OUTPUT_DIR_ESTADISTICA, exist_ok=True)

    operaciones = []

    # ---------------------------------------------------------
    # Cargar histórico existente
    # ---------------------------------------------------------
    try:
        with open(ARCHIVO_ESTADISTICA, "r", encoding="utf-8") as f:
            operaciones = json.load(f)

        if not isinstance(operaciones, list):
            operaciones = []

    except (FileNotFoundError, json.JSONDecodeError):
        operaciones = []

    # ---------------------------------------------------------
    # Evitar duplicados
    # ---------------------------------------------------------
    timestamp_apertura = posicion.get("timestamp_apertura")

    for operacion in operaciones:
        if (
            operacion.get("par") == par
            and operacion.get("timestamp_apertura") == timestamp_apertura
        ):
            print(
                f"  ⚠️ Operación ya registrada en estadísticas: "
                f"{par} | {timestamp_apertura}"
            )
            return

    # ---------------------------------------------------------
    # Determinar resultado
    # ---------------------------------------------------------
    if motivo_cierre == "SL":
        resultado = "PERDIDA"

    elif motivo_cierre == "BE":
        resultado = "BREAKEVEN"

    elif motivo_cierre == "TP3":
        resultado = "GANANCIA"

    else:
        resultado = motivo_cierre

    # ---------------------------------------------------------
    # Crear registro
    # ---------------------------------------------------------
    operacion = {
        "id_operacion": (
            f"{par.replace('/', '_').replace(':', '_')}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        ),

        "par": par,

        "direccion": posicion.get("direccion"),

        "timestamp_apertura": posicion.get("timestamp_apertura"),

        "timestamp_cierre": posicion.get("timestamp_cierre"),

        "precio_entrada": posicion.get("precio_entrada"),

        "precio_salida": precio_salida,

        "stop_loss_original": posicion.get("stop_loss_original"),

        "stop_loss_final": posicion.get("stop_loss_actual"),

        "tp1": posicion.get("tp1"),

        "tp2": posicion.get("tp2"),

        "tp3": posicion.get("tp3"),

        "tp1_alcanzado": posicion.get(
            "tp1_alcanzado",
            False,
        ),

        "tp2_alcanzado": posicion.get(
            "tp2_alcanzado",
            False,
        ),

        "tp3_alcanzado": posicion.get(
            "tp3_alcanzado",
            False,
        ),

        "sl_movido_be": posicion.get(
            "sl_movido_be",
            False,
        ),

        "motivo_cierre": motivo_cierre,

        "resultado": resultado,
    }

    operaciones.append(operacion)

    # ---------------------------------------------------------
    # Guardar histórico
    # ---------------------------------------------------------
    try:
        with open(
            ARCHIVO_ESTADISTICA,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                operaciones,
                f,
                indent=4,
                ensure_ascii=False,
            )

        print(
            f"  📊 Operación registrada en "
            f"{os.path.abspath(ARCHIVO_ESTADISTICA)}"
        )

    except Exception as e:
        print(
            f"  ❌ Error guardando estadística: {e}"
        )