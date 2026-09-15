import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Emoji según la dirección de la señal. NEUTRAL cubre casos donde no hay
# tendencia clara en el HTF (ver htf_filter.py).
EMOJI_POR_DIRECCION = {
    "LONG": "🟢",
    "SHORT": "🔴",
    "NEUTRAL": "⚪",
}


def _obtener_credenciales() -> tuple[str, str] | None:
    """
    Lee el token del bot y el chat_id desde variables de entorno.

    Se usan variables de entorno (no config.py) a propósito: son credenciales
    sensibles y NUNCA deben quedar hardcodeadas en el código fuente ni
    subirse al repositorio. En GitHub Actions se inyectan desde Secrets.

    Devuelve None si alguna de las dos falta, para que el llamador decida
    cómo actuar (en nuestro caso, omitir el envío sin romper la ejecución).
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
    riesgo: dict | None = None,
) -> None:
    """
    Envía una alerta de Telegram con el estado de la estrategia para un par.

    Si se proporciona 'riesgo' (plan de SL/TP/apalancamiento calculado por
    gestion_riesgo.calcular_gestion_riesgo), se añade como bloque adicional
    al mensaje. Si es None, el mensaje se envía solo con los datos básicos
    de la señal (comportamiento equivalente al de antes de añadir riesgo).

    Si las credenciales no están configuradas, la función avisa por consola
    y retorna sin lanzar excepción: una notificación fallida NUNCA debe
    interrumpir el análisis del resto de pares.
    """
    credenciales = _obtener_credenciales()
    if credenciales is None:
        print("  ℹ️ Notificación Telegram omitida (faltan TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return

    token, chat_id = credenciales

    emoji = EMOJI_POR_DIRECCION.get(senal, "⚪")
    score_texto = f"{score}/100" if score is not None else "N/D"

    mensaje = (
        f"{emoji} *{par}* | {senal}\n"
        f"Score: {score_texto}\n\n"
        f"Precio: ${precio:,.4f}\n"
    )

    # ---------- Bloque adicional con el plan de riesgo, si se proporciona ----------
    if riesgo:
        aviso_limite = " ⚠️" if riesgo.get("apalancamiento_limitado") else ""
        mensaje += (
            f"\n\n📐 *Plan de riesgo*\n"
            f"SL: ${riesgo['stop_loss']:,.4f} ({riesgo['distancia_sl_pct']}%)\n"
            f"TP1: ${riesgo['tp1']:,.4f}\n"
            f"TP2: ${riesgo['tp2']:,.4f}\n"
            f"TP3: ${riesgo['tp3']:,.4f}\n"
            f"Apalancamiento: {riesgo['apalancamiento_sugerido']}x{aviso_limite}\n"
            f"Tamaño posición: ${riesgo['tamano_posicion_usdt']:,.2f}\n\n"
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
        # Mostramos también el cuerpo de la respuesta de Telegram, que suele
        # traer el motivo exacto del error (ej. "chat not found").
        detalle = ""
        if e.response is not None:
            detalle = f" | Detalle: {e.response.text}"
        print(f"  ❌ Error al enviar alerta de Telegram para {par}: {e}{detalle}")