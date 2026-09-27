"""
CONFIGURACIÓN GENERAL DEL BOT DE TRADING
========================================
Modifica los valores de este archivo para ajustar el comportamiento
del bot, exchanges, indicadores y pares a analizar.
"""
import os

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
# Telegram
# ==============================================================================
TELEGRAM_TOKEN: str = os.environ.get("TELEGRAM_TOKEN", "PON_AQUI_TU_TOKEN")
TELEGRAM_CHAT_ID: str = os.environ.get("TELEGRAM_CHAT_ID", "PON_AQUI_TU_CHAT_ID")


# ==============================================================================
# 2. MERCADO, MONEDAS Y TEMPORALIDAD
# ==============================================================================
# Listado de pares a monitorizar
# Puedes añadir o quitar criptomonedas según tus preferencias
LISTADO_MONEDAS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "XRP/USDT:USDT",
    "BCH/USDT:USDT",
    "SUI/USDT:USDT",
    "XLM/USDT:USDT",
    "INJ/USDT:USDT",
    "HBAR/USDT:USDT",
    "ADA/USDT:USDT",
    "AVAX/USDT:USDT",
    "LTC/USDT:USDT",
    "AAVE/USDT:USDT",
    "ICP/USDT:USDT",
    "OP/USDT:USDT",
    "NEAR/USDT:USDT",
    "XMR/USDT:USDT",
    "DOGE/USDT:USDT",
    "UNI/USDT:USDT",
    "FIL/USDT:USDT",
    "ATOM/USDT:USDT",
    "LINK/USDT:USDT",
    "DOT/USDT:USDT",
    "ETC/USDT:USDT",
    "APT/USDT:USDT",
    "ARB/USDT:USDT",
]

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
ATR_MULTIPLICADOR_SL = 1.5   # Distancia del Stop Loss en múltiplos de ATR (ej. 1.5x o 2.0x)
ATR_MULTIPLICADOR_TP = 2.0   # Take Profit dinámico (ej. ratio 1:1.5 de riesgo/beneficio)

# --- DMI / ADX ---
ADX_PERIODO = 14
ADX_UMBRAL_TENDENCIA = 25.0  # Por encima de este valor se considera tendencia con fuerza

# ==============================================================================
# 4. CONFIGURACIÓN DEL BUCLE DE EJECUCIÓN (RUNTIME)
# ==============================================================================
# Tiempo de espera en segundos entre cada ciclo de análisis
INTERVALO_SEGUNDOS = 60

# ==============================================================================
# 5. ESTRATEGIA MULTI-TIMEFRAME
# ==============================================================================
# Modelo de puntuación (0-100) que combina un filtro de tendencia en un
# timeframe superior (HTF) con un filtro obligatorio y un score ponderado
# en el timeframe operativo, para generar señales LONG/SHORT.

# --- Timeframes del modelo ---
TIMEFRAME_ENTRADA = "5m"    # Timeframe operativo: donde se calcula el score y se dispara la entrada
TIMEFRAME_TENDENCIA = "15m"  # Timeframe HTF: define el sesgo (bias) direccional del par

# --- Cantidad de velas a descargar por timeframe de la estrategia ---
# Se definen por separado de config.CANTIDAD_VELAS (que es para el análisis
# general en config.TIMEFRAME) porque cada timeframe de la estrategia necesita
# un histórico distinto:
#   - TIMEFRAME_ENTRADA (5m): necesita suficiente warm-up para EMA21, ADX(14)
#     y el lookback de estructura (HIGHEST_LOWEST_PERIODO=20).
#   - TIMEFRAME_TENDENCIA (15m): solo calcula EMA9/EMA21, necesita menos velas.
CANTIDAD_VELAS_ENTRADA = 200
CANTIDAD_VELAS_TENDENCIA = 120

# --- Mandatory Filter (5m) ---
# ADX mínimo exigido en el timeframe operativo para considerar que hay
# tendencia suficiente como para operar (más permisivo que ADX_UMBRAL_TENDENCIA,
# que se sigue usando para el análisis de 1h en test_conexion_velas.py).
ADX_MINIMO_MANDATORY = 25.0

# --- Componente STRUCTURE (Breakout) ---
# Nº de velas hacia atrás (excluyendo la actual) para calcular el máximo/mínimo
# reciente y detectar rupturas de estructura (breakout).
HIGHEST_LOWEST_PERIODO = 20

# --- Componente VOLUME ---
# Periodo de la media móvil simple de volumen, usada para calcular el ratio
# volumen_actual / Volumen_SMA y puntuar picos de actividad.
VOLUME_SMA_PERIODO = 20

# --- Score y entrada ---
# Puntuación mínima (sobre 100) que debe alcanzar el score compuesto para
# considerar una entrada válida. La señal se dispara solo en el CRUCE hacia
# arriba de este umbral (score actual >= umbral Y score anterior < umbral).
SCORE_ENTRADA_MINIMO = 80.0

# --- Desglose de puntos máximos por componente del score (deben sumar 100) ---
PUNTOS_HTF_BIAS = 20
PUNTOS_TREND = 25
PUNTOS_RSI = 15
PUNTOS_ADX = 15
PUNTOS_VOLUME = 10
PUNTOS_STRUCTURE = 15

# ==============================================================================
# 6. GESTIÓN DE RIESGO (SL / TP / Apalancamiento)
# ==============================================================================

# --- Capital y riesgo por operación ---
CAPITAL_TOTAL_USDT = 1000.0          # Capital total de la cuenta (ajusta a tu caso real)
CAPITAL_POR_OPERACION_USDT = 100.0   # Margen fijo que usas en CADA operación, en USDT
PCT_PERDIDA_MAXIMA_SL = 10.0         # % del capital DE ESA OPERACIÓN que se pierde si salta el SL

# --- Límite de seguridad del apalancamiento ---
# Si la distancia al SL es muy pequeña, la fórmula podría pedir un apalancamiento
# irreal/peligroso. Este tope lo evita (se recorta y se marca con un aviso).
APALANCAMIENTO_MAXIMO = 50.0

# --- Stop Loss ---
# El SL se calcula sobre el swing low/high de las últimas N velas (mismo
# lookback que ya usa el componente STRUCTURE de la estrategia: config.HIGHEST_LOWEST_PERIODO),
# con un pequeño buffer adicional en múltiplos de ATR para no quedar pegado
# exactamente al nivel (evita saltos por 'spikes' de mecha).
SL_BUFFER_ATR_MULT = 1.0

# --- Take Profit (Riesgo:Beneficio) ---
# TP1/TP2/TP3 se calculan como múltiplos de la distancia al SL (riesgo),
# y se validan contra el próximo nivel de estructura visible (swing
# high/low reciente) para saber si son realistas o quedan "fuera de rango".
RR_TP1 = 1.0   # 1:1 -> mismo riesgo que beneficio
RR_TP2 = 1.5   # 1:2
RR_TP3 = 2.0   # 1:3

# ==============================================================================
# 7. COOLDOWN TRAS CIERRE DE POSICIÓN
# ==============================================================================
# Tras cerrar una posición, el par queda "en cooldown": no se evalúan nuevas
# señales de entrada hasta que pase el tiempo indicado. Objetivo: evitar
# reentradas inmediatas en un mercado que acaba de invalidar la operación.

# Cooldown estándar tras un cierre por BE o TP3 (operación resuelta con éxito
# o sin pérdida real).
COOLDOWN_HORAS_NORMAL = 4

# Si el par encadena SL_CONSECUTIVOS_PARA_COOLDOWN_LARGO stop loss SEGUIDOS
# (sin ningún BE/TP3 de por medio), el cooldown sube a este valor: el modelo
# está fallando repetidamente en ese par y conviene dejarlo más tiempo fuera.
COOLDOWN_HORAS_SL_CONSECUTIVOS = 12
SL_CONSECUTIVOS_PARA_COOLDOWN_LARGO = 2