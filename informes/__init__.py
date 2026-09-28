"""
Paquete de informes: calcula estadísticas sobre las operaciones cerradas
del bot y construye los informes que se envían por Telegram (resumen rápido
al cerrar una operación, informe diario e informe semanal).

Este __init__ está vacío a propósito: notificaciones/telegram_bot.py importa
informes.calculo, y el generador de informes (informes.generador) importa a su
vez notificaciones. Dejar aquí las importaciones vacías evita un ciclo.
"""