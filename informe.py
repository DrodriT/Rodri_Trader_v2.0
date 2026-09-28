import argparse

from informes.generador import generar_informe_diario, generar_informe_semanal


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera y envía por Telegram el informe diario o el semanal."
    )
    parser.add_argument("tipo", choices=["diario", "semanal"], help="Tipo de informe a enviar.")
    args = parser.parse_args()

    if args.tipo == "diario":
        generar_informe_diario()
    else:
        generar_informe_semanal()


if __name__ == "__main__":
    main()