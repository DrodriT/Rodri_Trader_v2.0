import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


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
    score: float,
    precio: float,
    timeframe_entrada: str,
) -> None:
    """
    Envía una alerta de Telegram cuando la estrategia detecta una señal de
    entrada (LONG/SHORT).

    Si las credenciales no están configuradas (por ejemplo, en pruebas
    locales sin variables de entorno), la función avisa por consola y
    retorna sin lanzar excepción: una notificación fallida NUNCA debe
    interrumpir el análisis del resto de pares.
    """
    credenciales = _obtener_credenciales()
    if credenciales is None:
        print("  ℹ️ Notificación Telegram omitida (faltan TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return

    token, chat_id = credenciales

    emoji = "🟢" if senal == "LONG" else "🔴"
    mensaje = (
        f"{emoji} *SEÑAL {senal}* — {par}\n"
        f"Precio: ${precio:,.4f}\n"
        f"Score: {score}/100\n"
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
        print(f"  ❌ Error al enviar alerta de Telegram para {par}: {e}")