import json
import os
from datetime import datetime, timezone

import ccxt
import pandas as pd

# Importamos las variables directamente desde config.py
import config

# Importamos nuestros indicadores modulares
from indicadores import (
    calcular_atr,
    calcular_dm,
    calcular_ema,
    calcular_rsi,
    calcular_stop_loss_atr,
    calcular_vwap,
)

# Carpeta raíz donde se organizan los resultados, con una subcarpeta por cada par (símbolo)
CARPETA_DATA = "data"
NOMBRE_ARCHIVO_RESULTADOS = "resultados.json"


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
            "defaultType":  config.MARKET_TYPE,
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


def descargar_velas(exchange, simbolo: str):
    """
    Descarga las últimas velas OHLCV y devuelve un DataFrame limpio.
    Incluye manejo de errores detallado.
    """
    print(f"\n📥 Descargando {config.CANTIDAD_VELAS} velas de {simbolo} ({config.TIMEFRAME})...")
    try:
        ohlcv = exchange.fetch_ohlcv(
            symbol=simbolo,
            timeframe=config.TIMEFRAME,
            limit=config.CANTIDAD_VELAS,
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
        print(f"❌ Error de red al consultar {simbolo}: {e}")
        return None
    except ccxt.ExchangeError as e:
        print(f"❌ Error del exchange al consultar {simbolo}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado consultando {simbolo}: {type(e).__name__} - {e}")
        return None

    columnas = ["timestamp", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(ohlcv, columns=columnas)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def obtener_ruta_resultados(par: str) -> str:
    """
    Construye (y crea si no existe) la ruta de la carpeta 'data/<PAR>/'
    y devuelve la ruta completa al archivo resultados.json de ese par.

    Ejemplo: obtener_ruta_resultados("BTCUSDT") -> "data/BTCUSDT/resultados.json"
    """
    carpeta_par = os.path.join(CARPETA_DATA, par)
    # exist_ok=True evita error si la carpeta ya existe (creación idempotente)
    os.makedirs(carpeta_par, exist_ok=True)
    return os.path.join(carpeta_par, NOMBRE_ARCHIVO_RESULTADOS)


def guardar_resultado_par(par: str, resultado: dict) -> None:
    """
    Guarda el resultado de UN par en su propio archivo data/<PAR>/resultados.json,
    añadiéndolo al histórico existente (no lo sobrescribe).

    Cada entrada queda marcada con su timestamp UTC, exchange y timeframe,
    de forma que más adelante se puedan calcular estadísticas por símbolo
    (evolución del RSI, ADX medio, volatilidad histórica, etc.).
    """
    ruta_archivo = obtener_ruta_resultados(par)

    entrada = {
        "fecha_hora_utc": datetime.now(timezone.utc).isoformat(),
        "exchange": config.EXCHANGE_ID,
        "timeframe": config.TIMEFRAME,
        **resultado,
    }

    # Cargamos el histórico existente de este par (si lo hay)
    historico = []
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)
            if isinstance(contenido, list):
                historico = contenido
    except (FileNotFoundError, json.JSONDecodeError):
        # Primera vez que se analiza este par, o archivo corrupto/vacío -> empezamos de cero
        historico = []

    historico.append(entrada)

    try:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=4)
        print(f"  💾 Guardado en '{ruta_archivo}' (histórico: {len(historico)} registros)")
    except Exception as e:
        print(f"  ❌ Error al guardar resultados de {par} en JSON: {e}")


def main():
    exchange = inicializar_exchange()

    print(f"\n=== INICIANDO ANÁLISIS EN {config.EXCHANGE_ID.upper()} (MAINNET) ===")
    print(f"Pares a consultar: {config.LISTADO_MONEDAS}")
    print(f"Temporalidad: {config.TIMEFRAME} | Velas: {config.CANTIDAD_VELAS}\n")

    for par in config.LISTADO_MONEDAS:
        df = descargar_velas(exchange, par)
        if df is None:
            continue

        try:
            # Cálculo de indicadores
            df["EMA_rapida"] = calcular_ema(df, periodo=config.EMA_RAPIDA_PERIODO)
            df["EMA_lenta"] = calcular_ema(df, periodo=config.EMA_LENTA_PERIODO)
            df["RSI"] = calcular_rsi(df, periodo=config.RSI_PERIODO)
            df["ATR"] = calcular_atr(df, periodo=config.ATR_PERIODO)
            df["VWAP"] = calcular_vwap(df)

            dmi = calcular_dm(df, periodo=config.ADX_PERIODO)
            df["ADX"] = dmi["ADX"]

            # Última vela
            ultima_vela = df.iloc[-1]
            precio_actual = ultima_vela["close"]
            sl_long = calcular_stop_loss_atr(
                precio_actual,
                ultima_vela["ATR"],
                multiplicador=config.ATR_MULTIPLICADOR_SL,
                direccion="LONG",
            )

            print(f"--- Resumen {par} ---")
            print(f"  Precio actual:     ${precio_actual:,.2f}")
            print(f"  EMA({config.EMA_RAPIDA_PERIODO}):         ${ultima_vela['EMA_rapida']:,.2f}")
            print(f"  EMA({config.EMA_LENTA_PERIODO}):        ${ultima_vela['EMA_lenta']:,.2f}")
            print(f"  RSI({config.RSI_PERIODO}):         {ultima_vela['RSI']:.2f}")
            print(f"  ADX({config.ADX_PERIODO}):         {ultima_vela['ADX']:.2f}")
            print(f"  SL sugerido LONG:  ${sl_long:,.2f} (a {config.ATR_MULTIPLICADOR_SL}x ATR)")

            # Empaquetamos el resultado de este par (convertimos a float nativo,
            # ya que los valores de pandas/numpy no son serializables por json.dump)
            resultado = {
                "precio_actual": round(float(precio_actual), 2),
                "ema_rapida": round(float(ultima_vela["EMA_rapida"]), 2),
                "ema_lenta": round(float(ultima_vela["EMA_lenta"]), 2),
                "rsi": round(float(ultima_vela["RSI"]), 2),
                "adx": round(float(ultima_vela["ADX"]), 2),
                "stop_loss_long": round(float(sl_long), 2),
            }

            # Guardamos inmediatamente en data/<PAR>/resultados.json
            guardar_resultado_par(par, resultado)
            print()

        except Exception as e:
            print(f"❌ Error procesando indicadores para {par}: {e}\n")


if __name__ == "__main__":
    main()