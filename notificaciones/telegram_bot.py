import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

EMOJI_POR_DIRECCION = {
    "LONG": "🟢",
    "SHORT": "🔴",
    "NEUTRAL": "⚪",
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


def enviar_alerta(
    par: str,
    senal: str,
    score: float | None,
    precio: float,
    timeframe_entrada: str,
) -> None:
    """
    Envía una alerta de Telegram con el estado de la estrategia para un par.
    """
    credenciales = _obtener_credenciales()
    if credenciales is None:
        print("  ℹ️ Notificación Telegram omitida (faltan TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return

    token, chat_id = credenciales

    emoji = EMOJI_POR_DIRECCION.get(senal, "⚪")
    score_texto = f"{score}/100" if score is not None else "N/D"

    mensaje = (
        f"{emoji} *{senal}* — {par}\n"
        f"Precio: ${precio:,.4f}\n"
        f"Score: {score_texto}\n"
        f"Timeframe: {timeframe_entrada}"
    )

    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown",
    }

    try:
        respuesta = requests.post(url, data=payload, timeout=10)
        respuesta.raise_for_status()
        print(f"  📨 Alerta de Telegram enviada para {par}.")
    except requests.exceptions.RequestException as e:
        detalle = ""
        if e.response is not None:
            detalle = f" | Detalle: {e.response.text}"
        print(f"  ❌ Error al enviar alerta de Telegram para {par}: {e}{detalle}")