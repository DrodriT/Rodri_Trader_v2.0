"""
Paquete de notificaciones: canales de alerta externos (Telegram, y en el
futuro otros como Discord o email). Expone una única función pública para
que el resto del proyecto no dependa de los detalles internos de cada canal.
"""

from .telegram_bot import (
    enviar_alerta,
    enviar_actualizacion_posicion,
)

__all__ = [
    "enviar_alerta",
    "enviar_actualizacion_posicion",
]