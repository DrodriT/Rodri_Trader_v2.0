import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

EMOJI_POR_DIRECCION = {
    "LONG": "🟢",
    "SHORT": "🔴",
    "NEUTRAL": "⚪",
}

# Emoji y texto según el tipo de evento de una posición ya abierta.
EVENTOS_POSICION = {
    "TP1_TOCADO": ("✅", "TP1 alcanzado"),
    "TP2_TOCADO": ("🔥", "TP2 alcanzado"),
    "TP3_TOCADO": ("🏆", "TP3 alcanzado — Posición cerrada con éxito"),
    "SL_TOCADO": ("❌", "SL tocado — Posición cerrada"),
    "BE_TOCADO": ("⚖️", "BE tocado (TP1 asegurado)"),
}


def _obtener_credenciales() -> tuple[str, str] | None:
    """
    Lee el token del bot y el chat_id desde variables de entorno.
    Devuelve None si alguna de las dos falta.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return None
    return token, chat_id


def _enviar_mensaje(mensaje: str, contexto: str) -> None:
    """
    Función interna compartida: envía un mensaje ya formateado a Telegram.
    'contexto' es solo para los logs de error (ej. nombre del par).
    """
    credenciales = _obtener_credenciales()
    if credenciales is None:
        print("  ℹ️ Notificación Telegram omitida (faltan TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return

    token, chat_id = credenciales
    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown",
    }

    try:
        respuesta = requests.post(url, data=payload, timeout=10)
        respuesta.raise_for_status()
        print(f"  📨 Notificación de Telegram enviada ({contexto}).")
    except requests.exceptions.RequestException as e:
        detalle = ""
        if e.response is not None:
            detalle = f" | Detalle: {e.response.text}"
        print(f"  ❌ Error al enviar notificación de Telegram ({contexto}): {e}{detalle}")


def enviar_alerta(
    par: str,
    senal: str,
    score: float | None,
    precio: float,
    timeframe_entrada: str,
    riesgo: dict | None = None,
) -> None:
    """
    Envía una alerta de Telegram cuando la estrategia detecta una NUEVA
    señal de entrada (LONG/SHORT), incluyendo el plan de riesgo si se
    proporciona.
    """
    emoji = EMOJI_POR_DIRECCION.get(senal, "⚪")
    score_texto = f"{score}/100" if score is not None else "N/D"

    mensaje = (
        f"{emoji} *{senal}* — {par}\n"
        f"Score: {score_texto}\n\n"
        f"💰 Entrada: ${precio:,.4f}\n"
       
    )

    if riesgo:
        aviso_limite = " ⚠️" if riesgo.get("apalancamiento_limitado") else ""
        mensaje += (
            f"\n\n📐 *Plan de riesgo*\n"
            f"⚡ Apalancamiento: {riesgo['apalancamiento_sugerido']}x{aviso_limite}\n"
            f"🔴 Stop Loss: ${riesgo['stop_loss']:,.4f} ({riesgo['distancia_sl_pct']}%)\n"
            f"🎯 TP1: ${riesgo['tp1']:,.4f}\n"
            f"🎯 TP2: ${riesgo['tp2']:,.4f}\n"
            f"🎯 TP3: ${riesgo['tp3']:,.4f}\n"
            
            f"Tamaño posición: ${riesgo['tamano_posicion_usdt']:,.2f}"
        )

    _enviar_mensaje(mensaje, contexto=f"entrada {par}")


def enviar_actualizacion_posicion(
    par: str,
    evento: str,
    posicion: dict,
    precio_actual: float,
) -> None:
    """
    Envía una notificación de Telegram sobre una posición YA ABIERTA:
    TP1/TP2/TP3 alcanzado, SL tocado, o cierre en breakeven.

    'evento' debe ser una de las claves de EVENTOS_POSICION (ver arriba).
    """
    emoji, titulo = EVENTOS_POSICION.get(evento, ("ℹ️", evento))

    mensaje = (
        f"{par} — {emoji} *{titulo}*\n"
        f"Entrada: ${posicion['precio_entrada']:,.4f}\n"
        f"Precio actual: ${precio_actual:,.4f}"
    )

    if evento == "TP1_TOCADO":
        mensaje += f"\n🔒 SL movido a BE: ${posicion['stop_loss_actual']:,.4f}"

    _enviar_mensaje(mensaje, contexto=f"{evento} {par}")