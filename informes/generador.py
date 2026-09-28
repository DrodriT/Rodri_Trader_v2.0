from datetime import datetime, timedelta

from notificaciones.grafico import generar_grafico_semanal
from notificaciones.telegram_bot import enviar_informe

from .calculo import (
    ahora_local,
    agrupar_por_dia,
    cargar_operaciones,
    curva_capital,
    filtrar_periodo,
    rango_semana,
)
from .mensajes import (
    DIAS_SEMANA,
    construir_informe_diario,
    construir_informe_semanal,
)
import config


def generar_informe_diario(ahora: datetime | None = None) -> None:
    """Construye el informe del día y lo envía por Telegram (solo texto)."""
    ahora = ahora or ahora_local()
    mensaje = construir_informe_diario(ahora)
    enviar_informe(mensaje, contexto="informe diario")


def generar_informe_semanal(ahora: datetime | None = None) -> None:
    """
    Construye el informe de la semana, genera el gráfico (curva de capital
    y PnL por día) y lo envía por Telegram: primero la imagen con un título
    corto (Telegram limita el pie de foto a 1024 caracteres) y después el
    texto completo.
    """
    ahora = ahora or ahora_local()
    mensaje = construir_informe_semanal(ahora)

    inicio, fin = rango_semana(ahora)
    todas = cargar_operaciones()
    ops_semana = filtrar_periodo(todas, inicio, fin)
    dias = agrupar_por_dia(ops_semana, inicio)

    ruta_grafico = generar_grafico_semanal(
        capitales=curva_capital(todas),
        indice_inicio_semana=len([o for o in todas if o["cierre"] < inicio]),
        etiquetas_dias=[DIAS_SEMANA[d["fecha"].weekday()] for d in dias],
        pnl_dias=[d["pnl"] for d in dias],
        capital_inicial=config.CAPITAL_TOTAL_USDT,
    )

    ultimo_dia = fin - timedelta(days=1)
    titulo = (
        f"📊 *Informe semanal* — {inicio.strftime('%d/%m')} al "
        f"{ultimo_dia.strftime('%d/%m/%Y')}"
    )
    enviar_informe(mensaje, ruta_grafico=ruta_grafico, caption=titulo, contexto="informe semanal")