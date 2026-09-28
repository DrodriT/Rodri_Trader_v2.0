import argparse
import os
import shutil
from datetime import datetime

# Carpetas cuyo contenido se borra al reiniciar el bot. Cada una guarda un
# tipo de estado que el bot va acumulando entre ejecuciones:
#   - indicadores : último snapshot por par (incluye el score previo que usa
#                   la estrategia para detectar el cruce del umbral)
#   - posiciones  : posiciones abiertas/cerradas por par
#   - estadistica : histórico de operaciones cerradas (operaciones.json)
#   - cooldown    : bloqueos temporales por par tras un cierre
CARPETAS_A_LIMPIAR = [
    os.path.join("data", "indicadores"),
    os.path.join("data", "posiciones"),
    os.path.join("data", "estadistica"),
    os.path.join("data", "cooldown"),
]

# Ruta del histórico de operaciones y carpeta donde se guarda la copia de
# seguridad opcional (esta carpeta NO se limpia nunca).
ARCHIVO_OPERACIONES = os.path.join("data", "estadistica", "operaciones.json")
CARPETA_COPIAS = os.path.join("data", "historico")


def _contar_archivos(carpeta: str) -> int:
    """Cuenta los archivos (recursivamente) que contiene una carpeta."""
    if not os.path.isdir(carpeta):
        return 0
    return sum(len(archivos) for _, _, archivos in os.walk(carpeta))


def _guardar_copia_operaciones() -> str | None:
    """
    Copia data/estadistica/operaciones.json a data/historico/ con marca de
    tiempo, para poder comparar más adelante el test antiguo con el nuevo.
    Devuelve la ruta de la copia, o None si no había histórico que guardar.
    """
    if not os.path.isfile(ARCHIVO_OPERACIONES):
        return None

    os.makedirs(CARPETA_COPIAS, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(CARPETA_COPIAS, f"operaciones_{marca}.json")
    shutil.copy2(ARCHIVO_OPERACIONES, destino)
    return destino


def _vaciar_carpeta(carpeta: str) -> int:
    """
    Borra todo el contenido de una carpeta (archivos y subcarpetas) pero
    deja la carpeta en sí. Devuelve cuántos elementos se borraron.
    """
    if not os.path.isdir(carpeta):
        return 0

    borrados = 0
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        try:
            if os.path.isdir(ruta):
                shutil.rmtree(ruta)
            else:
                os.remove(ruta)
            borrados += 1
        except OSError as e:
            print(f"  ❌ No se pudo borrar {ruta}: {e}")
    return borrados


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reinicia el bot: borra posiciones, cooldowns, snapshots "
                    "de indicadores e histórico de operaciones."
    )
    parser.add_argument(
        "--guardar-copia",
        action="store_true",
        help="Antes de borrar, guarda una copia de operaciones.json en data/historico/.",
    )
    parser.add_argument(
        "--si",
        action="store_true",
        help="No pedir confirmación (para uso automatizado).",
    )
    args = parser.parse_args()

    print("=== REINICIO DEL BOT ===")
    total = 0
    for carpeta in CARPETAS_A_LIMPIAR:
        n = _contar_archivos(carpeta)
        total += n
        print(f"  {carpeta}: {n} archivo(s)")

    if total == 0:
        print("\nNo hay nada que borrar. Saliendo.")
        return

    if not args.si:
        respuesta = input(f"\nSe borrarán {total} archivo(s). Escribe RESET para confirmar: ")
        if respuesta.strip() != "RESET":
            print("Cancelado. No se ha borrado nada.")
            return

    if args.guardar_copia:
        copia = _guardar_copia_operaciones()
        if copia:
            print(f"\n💾 Copia del histórico guardada en {copia}")
        else:
            print("\nℹ️ No había operaciones.json que guardar.")

    print()
    for carpeta in CARPETAS_A_LIMPIAR:
        borrados = _vaciar_carpeta(carpeta)
        print(f"  🗑️  {carpeta}: {borrados} elemento(s) borrado(s)")

    print("\n✅ Reinicio completado. El bot empezará de cero en la próxima ejecución.")


if __name__ == "__main__":
    main()