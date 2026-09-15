import ccxt
import pandas as pd
import json
import os

# Importamos las variables directamente desde config.py
import config

# Importamos nuestros indicadores modulares
from indicadores import (
    calcular_atr,
    calcular_dm,
    calcular_ema,
    calcular_rsi,
    calcular_stop_loss_atr,
)

# Importamos la estrategia (Algorithmic Entry Model V1.0)
from estrategia import generar_senal

# Importamos las notificaciones (Telegram)
from notificaciones import enviar_alerta

# Carpeta donde se guardará un JSON por cada par analizado
OUTPUT_DIR = os.path.join("data", "indicadores")


def get_default_type(exchange_id: str) -> str:
    """
    Devuelve el valor correcto para 'options.defaultType' según el exchange.
    - Binance (incluyendo binanceusdm) usa 'future'.
    - Bitget, Bybit, OKX, Kraken, KuCoin, etc. usan 'swap'.
    """
    exchange_lower = exchange_id.lower()
    if "binance" in exchange_lower:
        return "future"
    else:
        return "swap"


def inicializar_exchange():
    """
    Crea la instancia del exchange.
    - SIEMPRE se conecta a la red principal (mainnet).
    - Configura automáticamente el tipo de mercado (futuros perpetuos).
    - Solo usa API keys si están definidas y no vacías.
    """
    try:
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
    except AttributeError:
        raise ValueError(
            f"❌ Exchange '{config.EXCHANGE_ID}' no soportado por CCXT. "
            "Revisa la lista en https://docs.ccxt.com/#/README?id=exchanges"
        )

    exchange_config = {
        "enableRateLimit": True,
        "timeout": 30000,
        "options": {
            "defaultType": config.MARKET_TYPE,
        },
    }

    if hasattr(config, 'API_KEY') and config.API_KEY and config.API_KEY.strip():
        exchange_config["apiKey"] = config.API_KEY
        exchange_config["secret"] = config.API_SECRET
        print("🔑 Usando API keys (privadas) para el exchange.")
    else:
        print("🌐 Sin API keys - solo acceso a datos públicos.")

    exchange = exchange_class(exchange_config)

    print(f"🔗 Conectado a {config.EXCHANGE_ID.upper()} (Mainnet) - Tipo: {config.MARKET_TYPE}")

    return exchange


def descargar_velas(exchange, simbolo: str, timeframe: str, cantidad: int):
    """
    Descarga las últimas velas OHLCV de un timeframe concreto y devuelve
    un DataFrame limpio. Incluye manejo de errores detallado.
    """
    print(f"📥 Descargando {cantidad} velas de {simbolo} ({timeframe})...")
    try:
        ohlcv = exchange.fetch_ohlcv(
            symbol=simbolo,
            timeframe=timeframe,
            limit=cantidad,
        )

    except ccxt.BadSymbol as e:
        print(f"❌ Símbolo '{simbolo}' no válido para {config.EXCHANGE_ID}.")
        print(f"   Detalle: {e}")
        try:
            exchange.load_markets()
            valid_symbols = list(exchange.markets.keys())[:10]
            print(f"   Ejemplos de símbolos válidos: {valid_symbols}")
        except Exception:
            pass
        return None
    except ccxt.NetworkError as e:
        print(f"❌ Error de red al consultar {simbolo} ({timeframe}): {e}")
        return None
    except ccxt.ExchangeError as e:
        print(f"❌ Error del exchange al consultar {simbolo} ({timeframe}): {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado consultando {simbolo} ({timeframe}): {type(e).__name__} - {e}")
        return None

    columnas = ["timestamp", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(ohlcv, columns=columnas)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def calcular_indicadores_entrada(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula TODOS los indicadores necesarios en el timeframe operativo
    (config.TIMEFRAME_ENTRADA, ej. 5m): EMA rápida/lenta, RSI, ATR y ADX.
    """
    df = df.copy()
    df["EMA_rapida"] = calcular_ema(df, periodo=config.EMA_RAPIDA_PERIODO)
    df["EMA_lenta"] = calcular_ema(df, periodo=config.EMA_LENTA_PERIODO)
    df["RSI"] = calcular_rsi(df, periodo=config.RSI_PERIODO)
    df["ATR"] = calcular_atr(df, periodo=config.ATR_PERIODO)

    dmi = calcular_dm(df, periodo=config.ADX_PERIODO)
    df["ADX"] = dmi["ADX"]
    return df


def calcular_indicadores_tendencia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los indicadores mínimos necesarios en el timeframe HTF
    (config.TIMEFRAME_TENDENCIA, ej. 15m) para que la estrategia pueda
    evaluar el HTF Filter: EMA rápida/lenta.
    """
    df = df.copy()
    df["EMA_rapida"] = calcular_ema(df, periodo=config.EMA_RAPIDA_PERIODO)
    df["EMA_lenta"] = calcular_ema(df, periodo=config.EMA_LENTA_PERIODO)
    return df


def obtener_simbolo_base(par: str) -> str:
    """
    Extrae el nombre 'base' de la moneda a partir del símbolo del par,
    sin importar el formato exacto que use el exchange.

    Ejemplos:
        "BTC/USDT:USDT" -> "BTC"
        "BTC/USDT"      -> "BTC"
        "BTCUSDT"       -> "BTC"   (si termina en USDT y no tiene separadores)
    """
    if "/" in par:
        return par.split("/")[0]

    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if par.upper().endswith(quote):
            return par.upper().removesuffix(quote)

    return par


def leer_estrategia_previa(par: str) -> dict | None:
    """
    Lee el bloque 'estrategia' guardado en la ÚLTIMA EJECUCIÓN real para este
    par, desde su archivo data/indicadores/<BASE>.json, si existe.

    Se usa como referencia auténtica de 'score_anterior' en generar_senal(),
    para detectar cruces de umbral ENTRE ejecuciones distintas del bot.

    Devuelve None si es la primera vez que se analiza este par (archivo no
    existe todavía) o si el archivo está corrupto/incompleto.
    """
    nombre_base = obtener_simbolo_base(par)
    ruta_json = os.path.join(OUTPUT_DIR, f"{nombre_base}.json")

    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            datos_previos = json.load(f)
        return datos_previos.get("estrategia")
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None


def guardar_resultado_par(par: str, datos: dict) -> None:
    """
    Guarda el resultado de un par en 'data/indicadores/<BASE>.json'.
    Sobrescribe el archivo con el último snapshot calculado para ese par.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    nombre_base = obtener_simbolo_base(par)
    ruta_json = os.path.join(OUTPUT_DIR, f"{nombre_base}.json")

    try:
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        print(f"  ✅ Datos guardados en {os.path.abspath(ruta_json)}")
    except Exception as e:
        print(f"  ❌ Error al guardar JSON en {ruta_json}: {e}")


def analizar_par(exchange, par: str) -> dict | None:
    """
    Descarga las velas de 5m (entrada) y 15m (tendencia) para el par,
    calcula todos los indicadores y evalúa la estrategia.

    Devuelve un diccionario con toda la información del par (indicadores +
    resultado de la estrategia), listo para imprimir y guardar en JSON.
    Devuelve None si falla la descarga de 5m (timeframe imprescindible,
    ya que de él salen el precio actual, el SL y el Mandatory Filter/Score).

    IMPORTANTE: 'resultado_estrategia' se inicializa SIEMPRE con un
    diccionario por defecto antes de cualquier rama condicional, para
    garantizar que nunca llegue a ser None en ningún camino de ejecución
    (evita el error 'NoneType' object has no attribute 'pop').
    """
    df_5m = descargar_velas(
        exchange, par, config.TIMEFRAME_ENTRADA, config.CANTIDAD_VELAS_ENTRADA
    )
    if df_5m is None:
        return None

    df_5m = calcular_indicadores_entrada(df_5m)
    ultima_vela = df_5m.iloc[-1]
    precio_actual = ultima_vela["close"]

    sl_long = calcular_stop_loss_atr(
        precio_actual,
        ultima_vela["ATR"],
        multiplicador=config.ATR_MULTIPLICADOR_SL,
        direccion="LONG",
    )

    # ---------- Valor por defecto: NUNCA debe quedar como None ----------
    resultado_estrategia = {
        "bias_htf": None,
        "cumple_mandatory": None,
        "score_actual": None,
        "score_anterior": None,
        "senal": None,
        "error": "No se pudieron descargar velas de 15m para evaluar la estrategia.",
    }

    # ---------- Timeframe HTF (15m) ----------
    df_15m = descargar_velas(
        exchange, par, config.TIMEFRAME_TENDENCIA, config.CANTIDAD_VELAS_TENDENCIA
    )

    if df_15m is not None:
        df_15m = calcular_indicadores_tendencia(df_15m)

        # Leemos el resultado de la ÚLTIMA ejecución real para este par,
        # ANTES de que este análisis lo sobrescriba más adelante en main().
        estrategia_previa = leer_estrategia_previa(par)

        resultado_estrategia = generar_senal(
            par, df_5m, df_15m, resultado_previo=estrategia_previa
        )
        resultado_estrategia.pop("par", None)  # ya va como clave superior del JSON

    return {
        "ultima_vela": ultima_vela,
        "precio_actual": precio_actual,
        "sl_long": sl_long,
        "estrategia": resultado_estrategia,
    }


def main():
    exchange = inicializar_exchange()

    print(f"\n=== INICIANDO ANÁLISIS EN {config.EXCHANGE_ID.upper()} (MAINNET) ===")
    print(f"Pares a consultar: {config.LISTADO_MONEDAS}")
    print(f"Entrada: {config.TIMEFRAME_ENTRADA} ({config.CANTIDAD_VELAS_ENTRADA} velas) "
          f"| Tendencia HTF: {config.TIMEFRAME_TENDENCIA} ({config.CANTIDAD_VELAS_TENDENCIA} velas)\n")

    for par in config.LISTADO_MONEDAS:
        try:
            analisis = analizar_par(exchange, par)
            if analisis is None:
                continue

            ultima_vela = analisis["ultima_vela"]
            precio_actual = analisis["precio_actual"]
            sl_long = analisis["sl_long"]
            resultado_estrategia = analisis["estrategia"]

            # ---------- IMPRESIÓN EN PANTALLA (resumen) ----------
            print(f"--- Resumen {par} ---")
            print(f"  Precio actual:     ${precio_actual:,.2f}")
            print(f"  EMA({config.EMA_RAPIDA_PERIODO}):         ${ultima_vela['EMA_rapida']:,.2f}")
            print(f"  EMA({config.EMA_LENTA_PERIODO}):        ${ultima_vela['EMA_lenta']:,.2f}")
            print(f"  RSI({config.RSI_PERIODO}):         {ultima_vela['RSI']:.2f}")
            print(f"  ADX({config.ADX_PERIODO}):         {ultima_vela['ADX']:.2f}")
            print(f"  SL sugerido LONG:  ${sl_long:,.2f} (a {config.ATR_MULTIPLICADOR_SL}x ATR)")

            # ---------- IMPRESIÓN EN PANTALLA (estrategia) ----------
            if resultado_estrategia.get("error"):
                print(f"  ⚠️ Estrategia: {resultado_estrategia['error']}\n")
            else:
                print(f"  --- Estrategia ({config.TIMEFRAME_ENTRADA}/{config.TIMEFRAME_TENDENCIA}) ---")
                print(f"  Sesgo HTF ({config.TIMEFRAME_TENDENCIA}):     {resultado_estrategia['bias_htf']}")
                print(f"  Mandatory Filter:      {'✅ Cumple' if resultado_estrategia['cumple_mandatory'] else '❌ No cumple'}")
                print(f"  Score actual:          {resultado_estrategia['score_actual']}/100")
                print(f"  Score anterior:        {resultado_estrategia['score_anterior']}/100")

                if resultado_estrategia["senal"]:
                    print(f"  🚀 SEÑAL DE ENTRADA:   {resultado_estrategia['senal']}")
                    enviar_alerta(
                        par=par,
                        senal=resultado_estrategia["senal"],
                        score=resultado_estrategia["score_actual"],
                        precio=float(precio_actual),
                        timeframe_entrada=config.TIMEFRAME_ENTRADA,
                    )
                else:
                    print("  Señal de entrada:      Ninguna (sin cruce de umbral)")
                print()

            # ---------- CONSTRUCCIÓN DEL JSON ----------
            # IMPORTANTE: convertimos todo a float()/str() nativos de Python,
            # ya que numpy.float64 / pandas.Timestamp NO son serializables
            # directamente por json.dump y provocarían un TypeError.
            datos_json = {
                "simbolo": par,
                "timestamp": ultima_vela["timestamp"].isoformat(),
                "precio_actual": round(float(precio_actual), 2),
                f"EMA_{config.EMA_RAPIDA_PERIODO}": round(float(ultima_vela["EMA_rapida"]), 2),
                f"EMA_{config.EMA_LENTA_PERIODO}": round(float(ultima_vela["EMA_lenta"]), 2),
                "RSI": round(float(ultima_vela["RSI"]), 2),
                "ADX": round(float(ultima_vela["ADX"]), 2),
                "ATR": round(float(ultima_vela["ATR"]), 2),
                "stop_loss_long": round(float(sl_long), 2),
                "multiplicador_SL": config.ATR_MULTIPLICADOR_SL,
                "timeframe": config.TIMEFRAME_ENTRADA,
                "velas_usadas": config.CANTIDAD_VELAS_ENTRADA,
                # ---------- Bloque de la estrategia multi-timeframe ----------
                "estrategia": {
                    "timeframe_entrada": config.TIMEFRAME_ENTRADA,
                    "timeframe_tendencia": config.TIMEFRAME_TENDENCIA,
                    **resultado_estrategia,
                },
            }

            # ---------- GUARDADO EN data/indicadores/<BASE>.json ----------
            guardar_resultado_par(par, datos_json)

        except Exception as e:
            print(f"❌ Error procesando indicadores para {par}: {e}\n")


if __name__ == "__main__":
    main()