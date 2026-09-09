"""
CONFIGURACIÓN GENERAL DEL BOT DE TRADING
========================================
Modifica los valores de este archivo para ajustar el comportamiento
del bot, exchanges, indicadores y pares a analizar.
"""

# ==============================================================================
# 1. CONFIGURACIÓN DEL EXCHANGE
# ==============================================================================
# Nombre del exchange soportado por ccxt (ej: 'binance', 'bybit', 'kraken', 'kucoin')
EXCHANGE_ID = "bitget"

# Tipo de mercado: 'spot', 'margin', 'future', 'swap', 'option', etc.
# Para futuros perpetuos USDT‑M, usa 'swap' (la mayoría) o 'future' (Binance).
MARKET_TYPE = "swap"   # <--- NUEVA VARIABLE

# Claves API (déjalas vacías por ahora si solo vas a leer velas y datos públicos)
API_KEY = ""
API_SECRET = ""

# ==============================================================================
# 2. MERCADO, MONEDAS Y TEMPORALIDAD
# ==============================================================================
# Listado de pares a monitorizar
# Puedes añadir o quitar criptomonedas según tus preferencias
LISTADO_MONEDAS = [
    "BTCUSDT",
    "BTC/USDT:USDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
]

# Temporalidad de las velas:
# Opciones habituales: '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'
TIMEFRAME = "1h"

# Cantidad de velas históricas a descargar para el cálculo (mínimo recomendado: 100)
CANTIDAD_VELAS = 150


# ==============================================================================
# 3. PARÁMETROS DE INDICADORES TÉCNICOS
# ==============================================================================

# --- RSI (Relative Strength Index) ---
RSI_PERIODO = 14
RSI_SOBRECOMPRA = 70.0  # Nivel por encima del cual se considera sobrecomprado
RSI_SOBREVENTA = 30.0   # Nivel por debajo del cual se considera sobrevendido

# --- Medias Móviles (EMA) ---
EMA_RAPIDA_PERIODO = 9    # Periodo de la EMA rápida (ej. 9 o 20)
EMA_LENTA_PERIODO = 21   # Periodo de la EMA lenta (ej. 21 o 50)
EMA_TENDENCIA_PERIODO = 200  # EMA institucional para filtro de tendencia mayor

# --- Medias Móviles Simples (SMA) ---
SMA_PERIODO = 20

# --- ATR (Average True Range) & Gestión de Riesgo ---
ATR_PERIODO = 14
ATR_MULTIPLICADOR_SL = 2.0   # Distancia del Stop Loss en múltiplos de ATR (ej. 1.5x o 2.0x)
ATR_MULTIPLICADOR_TP = 3.0   # Take Profit dinámico (ej. ratio 1:1.5 de riesgo/beneficio)

# --- DMI / ADX ---
ADX_PERIODO = 14
ADX_UMBRAL_TENDENCIA = 25.0  # Por encima de este valor se considera tendencia con fuerza


# ==============================================================================
# 4. CONFIGURACIÓN DEL BUCLE DE EJECUCIÓN (RUNTIME)
# ==============================================================================
# Tiempo de espera en segundos entre cada ciclo de análisis
INTERVALO_SEGUNDOS = 60
