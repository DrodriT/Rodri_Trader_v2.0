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


def inicializar_exchange():
    """Crea la instancia del exchange según config.py."""
    exchange_class = getattr(ccxt, config.EXCHANGE_ID)
    exchange = exchange_class({
        "enableRateLimit": True,  # Respeta límites de llamadas del exchange
    })

    if config.TESTNET_MODE and hasattr(exchange, "set_sandbox_mode"):
        try:
            exchange.set_sandbox_mode(True)
        except Exception:
            pass

    return exchange


def descargar_velas(exchange, simbolo: str):
    """Descarga las últimas velas OHLCV y devuelve un DataFrame limpio."""
    print(f"\nDescargando {config.CANTIDAD_VELAS} velas de {simbolo} ({config.TIMEFRAME})...")
    ohlcv = exchange.fetch_ohlcv(
        symbol=simbolo,
        timeframe=config.TIMEFRAME,
        limit=config.CANTIDAD_VELAS,
    )

    columnas = ["timestamp", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(ohlcv, columns=columnas)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def main():
    exchange = inicializar_exchange()

    print(f"=== INICIANDO CONEXIÓN A {config.EXCHANGE_ID.upper()} ===")
    print(f"Pares a consultar: {config.LISTADO_MONEDAS}")
    print(f"Temporalidad: {config.TIMEFRAME} | Velas: {config.CANTIDAD_VELAS}")

    for par in config.LISTADO_MONEDAS:
        try:
            df = descargar_velas(exchange, par)

            # Cálculo de indicadores usando los parámetros de config.py
            df["EMA_rapida"] = calcular_ema(df, periodo=config.EMA_RAPIDA_PERIODO)
            df["EMA_lenta"] = calcular_ema(df, periodo=config.EMA_LENTA_PERIODO)
            df["RSI"] = calcular_rsi(df, periodo=config.RSI_PERIODO)
            df["ATR"] = calcular_atr(df, periodo=config.ATR_PERIODO)
            df["VWAP"] = calcular_vwap(df)

            dmi = calcular_dm(df, periodo=config.ADX_PERIODO)
            df["ADX"] = dmi["ADX"]

            # Datos de la última vela cerrada / actual
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

        except Exception as e:
            print(f"❌ Error consultando {par}: {e}")


if __name__ == "__main__":
    main()
