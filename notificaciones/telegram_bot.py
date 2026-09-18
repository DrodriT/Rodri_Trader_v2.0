import os

import requests

import config
from .grafico import generar_grafico_operacion

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_API_URL_FOTO = "https://api.telegram.org/bot{token}/sendPhoto"

EMOJI_POR_DIRECCION = {
    "LONG": "🟢",
    "SHORT": "🔴",
    "NEUTRAL": "⚪",
}

# Emoji y texto compacto según el tipo de evento de una posición ya abierta.
# El texto es deliberadamente corto (estilo "ticker de resultados"): no se
# añade entrada/precio actual porque esos datos ya no aportan nada útil una
# vez la posición está en marcha o cerrada.
EVENTOS_POSICION = {
    "TP1_TOCADO": ("✅", "TP1 alcanzado. 🔒 SL movido a BE."),
    "TP2_TOCADO": ("🔥", "TP2 alcanzado. Runner hacia TP3."),
    "TP3_TOCADO": ("🏁", "TP3 alcanzado. Trade cerrado."),
    "SL_TOCADO": ("❌", "SL tocado. Trade cerrado."),
    "BE_TOCADO": ("⚖️", "BE tocado. Trade cerrado en breakeven."),
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


def _enviar_foto(ruta_imagen: str, caption: str, contexto: str) -> bool:
    """
    Envía una imagen a Telegram (sendPhoto) con el texto como 'caption'.
    Devuelve True si se envió correctamente, False si falló o si faltan
    credenciales, para que quien la llama pueda hacer fallback a texto plano.
    """
    credenciales = _obtener_credenciales()
    if credenciales is None:
        print("  ℹ️ Notificación Telegram omitida (faltan TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return False

    token, chat_id = credenciales
    url = TELEGRAM_API_URL_FOTO.format(token=token)

    try:
        with open(ruta_imagen, "rb") as archivo_imagen:
            respuesta = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
                files={"photo": archivo_imagen},
                timeout=20,
            )
        respuesta.raise_for_status()
        print(f"  📨🖼️ Gráfico enviado a Telegram ({contexto}).")
        return True
    except (requests.exceptions.RequestException, OSError) as e:
        detalle = ""
        if isinstance(e, requests.exceptions.RequestException) and e.response is not None:
            detalle = f" | Detalle: {e.response.text}"
        print(f"  ❌ Error al enviar gráfico a Telegram ({contexto}): {e}{detalle}")
        return False
    finally:
        # El PNG es temporal (se genera en cada señal): lo borramos una vez
        # enviado (o tras el intento fallido) para no acumular archivos.
        try:
            os.remove(ruta_imagen)
        except OSError:
            pass


def _formatear_par_compacto(par: str) -> str:
    """
    Convierte el símbolo tal y como lo usa ccxt/config (ej. 'BTC/USDT:USDT')
    a la forma compacta que se ve en Telegram (ej. 'BTCUSDT'), quitando la
    barra y el sufijo de liquidación (':USDT').
    """
    return par.replace("/", "").split(":")[0]


def _calcular_distancia_pct(precio_objetivo: float, precio_entrada: float) -> float:
    """Distancia porcentual entre un precio objetivo (TP/SL) y el precio de entrada."""
    if precio_entrada == 0:
        return 0.0
    return round(abs(precio_objetivo - precio_entrada) / precio_entrada * 100, 2)


def enviar_alerta(
    par: str,
    senal: str,
    score: float | None,
    precio: float,
    timeframe_entrada: str,
    riesgo: dict | None = None,
    df_5m=None,
) -> None:
    """
    Envía una alerta de Telegram cuando la estrategia detecta una NUEVA
    señal de entrada (LONG/SHORT).

    Formato compacto (estilo panel de señales), usando ÚNICAMENTE datos
    que ya calculamos en el propio bot: no se inventan campos como
    'Probabilidad', 'Setup' o 'Semáforo' que no forman parte del modelo.

    Si se recibe 'df_5m' (el DataFrame de velas del timeframe de entrada)
    y hay plan de riesgo, se genera y se envía un gráfico de velas con
    Entrada/SL/TP1/TP2/TP3 marcados, usando el texto de abajo como caption.
    Si no hay velas, o falla la generación/envío de la imagen, se hace
    fallback automático al mensaje de solo texto.
    """
    emoji = EMOJI_POR_DIRECCION.get(senal, "⚪")
    par_compacto = _formatear_par_compacto(par)
    exchange_nombre = config.EXCHANGE_ID.capitalize()

    mensaje = f"{emoji} *{par_compacto}* {senal} ({exchange_nombre})\n\n"
    mensaje += f"Entrada: {precio:,.4f}\n"

    if riesgo:
        aviso_limite = " ⚠️" if riesgo.get("apalancamiento_limitado") else ""
        precio_entrada = riesgo["precio_entrada"]

        mensaje += (
            f"SL: {riesgo['stop_loss']:,.4f} | SL%: {riesgo['distancia_sl_pct']}%\n"
            f"Lev. sugerido ({config.PCT_PERDIDA_MAXIMA_SL:g}%): "
            f"{riesgo['apalancamiento_sugerido']}x{aviso_limite}\n\n"
        )

        # RR de cada TP: es el mismo multiplicador fijo (config.RR_TP1/2/3)
        # que ya se usa en take_profit.py para calcular el propio nivel.
        niveles_tp = (
            ("TP1", riesgo["tp1"], config.RR_TP1),
            ("TP2", riesgo["tp2"], config.RR_TP2),
            ("TP3", riesgo["tp3"], config.RR_TP3),
        )
        for etiqueta, precio_tp, rr in niveles_tp:
            pct = _calcular_distancia_pct(precio_tp, precio_entrada)
            mensaje += f"{etiqueta}: {precio_tp:,.4f} | {pct}% | RR {rr:.2f}\n"

        mensaje += "\n"

    score_texto = f"{score}/100" if score is not None else "N/D"
    mensaje += f"Score: {score_texto}"
    mensaje = mensaje.strip()

    # Si tenemos velas y plan de riesgo, intentamos enviar el gráfico con
    # el mensaje como caption. Si algo falla (sin velas, sin crédito de
    # Telegram, error de red...), caemos al mensaje de solo texto de siempre.
    if df_5m is not None and riesgo:
        ruta_grafico = generar_grafico_operacion(df_5m, par, senal, riesgo)
        if ruta_grafico and _enviar_foto(ruta_grafico, mensaje, contexto=f"entrada {par}"):
            return

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

    Formato compacto de una sola línea (estilo panel de señales).
    'posicion' y 'precio_actual' se mantienen como parámetros por si en el
    futuro se necesitan, pero no se muestran: en este punto del ciclo de
    vida de la operación no aportan información nueva.

    'evento' debe ser una de las claves de EVENTOS_POSICION (ver arriba).
    """
    emoji, texto = EVENTOS_POSICION.get(evento, ("ℹ️", evento))
    par_compacto = _formatear_par_compacto(par)

    mensaje = f"{emoji} *{par_compacto}* – {texto}"

    _enviar_mensaje(mensaje, contexto=f"{evento} {par}")