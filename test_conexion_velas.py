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
    calcular_vwap,
)


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

    # Configuración base
    exchange_config = {
        "enableRateLimit": True,
        "timeout": 30000,
        "options": {
            "defaultType":  config.MARKET_TYPE,  
        },
    }

    # Solo añadir credenciales si existen y no están vacías
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
        # Opcional: mostrar los primeros 10 símbolos válidos del exchange
        try:
            exchange.load_markets()
            valid_symbols = list(exchange.markets.keys())[:10]
            print(f"   Ejemplos de símbolos válidos: {valid_symbols}")
        except:
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


def main():
    exchange = inicializar_exchange()

    # Crear la carpeta de salida si no existe
    output_dir = "./data/indicadores"
    os.makedirs(output_dir, exist_ok=True)

    # (Opcional) Cargar mercados para verificar símbolos disponibles
    # Esto es útil para depuración, pero ralentiza la primera ejecución.
    # exchange.load_markets()

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
            print(f"  SL sugerido LONG:  ${sl_long:,.2f} (a {config.ATR_MULTIPLICADOR_SL}x ATR)\n")

            # ---- Guardar en JSON ----
            datos_json = {
                "simbolo": par,
                "timestamp": ultima_vela["timestamp"].isoformat(),  # Fecha/hora de la última vela
                "precio_actual": round(precio_actual, 2),
                f"EMA_{config.EMA_RAPIDA_PERIODO}": round(ultima_vela["EMA_rapida"], 2),
                f"EMA_{config.EMA_LENTA_PERIODO}": round(ultima_vela["EMA_lenta"], 2),
                "RSI": round(ultima_vela["RSI"], 2),
                "ADX": round(ultima_vela["ADX"], 2),
                "ATR": round(ultima_vela["ATR"], 2),
                "stop_loss_long": round(sl_long, 2),
                "multiplicador_SL": config.ATR_MULTIPLICADOR_SL,
                "timeframe": config.TIMEFRAME,
                "velas_usadas": config.CANTIDAD_VELAS,
            }

            # Ruta del archivo: ./data/indicadores/par.json
            # Limpiamos el símbolo para usarlo como nombre de archivo (reemplazamos '/' por '_' por si acaso)
            nombre_archivo = par.replace("/", "_") + ".json"
            ruta_json = os.path.join(output_dir, nombre_archivo)

            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(datos_json, f, indent=4, ensure_ascii=False)

            print(f"  ✅ Datos guardados en {ruta_json}\n")
            
        except Exception as e:
            print(f"❌ Error procesando indicadores para {par}: {e}\n")


if __name__ == "__main__":
    main()