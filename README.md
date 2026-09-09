
<div align="center">


# 🤖 RODRI TRADER v2.0 — Bot de Trading Algorítmico

**Estrategia cuantitativa modular para mercados de criptomonedas (Futuros Perpetuos)**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![CCXT](https://img.shields.io/badge/CCXT-Exchange%20Connector-black?logo=bitcoin)
![Pandas](https://img.shields.io/badge/Pandas-DataFrames-150458?logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-Cálculo%20Numérico-013243?logo=numpy&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)
![Status](https://img.shields.io/badge/Estado-En%20Desarrollo-yellow)
![License](https://img.shields.io/badge/Licencia-MIT-lightgrey)

<img src="./assets/rodri_trader_logo.png" alt="Rodri Trader Logo" width="260"/>

</div>

---

## 📖 Descripción General

**Rodri Trader** es un bot de trading algorítmico desarrollado en **Python**, diseñado con una arquitectura **modular, escalable y mantenible**, siguiendo los principios **SOLID** y el estándar **PEP 8**.

El objetivo del proyecto es construir un sistema capaz de:

- 📡 Conectarse a exchanges de criptomonedas (actualmente **Bitget**, vía [CCXT](https://github.com/ccxt/ccxt)) para operar en el mercado de **Futuros Perpetuos**.
- 📊 Calcular en tiempo real un conjunto de **indicadores técnicos** clave (tendencia, momentum, volatilidad y volumen).
- 🧠 Evaluar señales de entrada/salida a través de una **estrategia configurable**.
- 🛡️ Gestionar el riesgo de cada operación mediante cálculo dinámico de **Stop Loss / Take Profit** basado en ATR.
- 🔔 (Próximamente) Enviar notificaciones automáticas de operaciones y estado del bot.

> ⚠️ **Aviso de riesgo:** este proyecto tiene fines educativos y de investigación. Operar con criptomonedas conlleva un riesgo elevado de pérdida de capital. Úsalo bajo tu propia responsabilidad.

---

## 🏗️ Arquitectura del Proyecto

El desarrollo se realiza de forma **incremental**, paso a paso. Actualmente el proyecto se encuentra en la fase de **validación de conexión al exchange y cálculo de indicadores**, sobre la que se irá construyendo la arquitectura completa.

### 📂 Estructura actual

```
RODRI_TRADER_V2.0/
│
├── .github/
│   └── workflows/
│       └── ejecutar_bot.yml     # Workflow de GitHub Actions (ejecución manual)
│
├── indicadores/                 # Paquete de indicadores técnicos (modular)
│   ├── __init__.py
│   ├── atr.py                   # Average True Range + Stop Loss dinámico
│   ├── dm.py                    # Directional Movement System (+DI, -DI, ADX)
│   ├── ema.py                   # Media Móvil Exponencial
│   ├── rsi.py                   # Índice de Fuerza Relativa (Wilder)
│   ├── sma.py                   # Media Móvil Simple
│   └── vwap.py                  # Precio Promedio Ponderado por Volumen
│
├── config.py                    # Configuración centralizada (exchange, pares, parámetros)
├── test_conexion_velas.py       # Script de prueba: conexión al exchange + cálculo de indicadores
├── test_indicadores.py          # Script de prueba: validación de indicadores con datos simulados
└── README.md
```

### 🎯 Estructura objetivo (roadmap de arquitectura)

```
trading_bot/
│
├── config/                 # Configuración general (parámetros, credenciales)
├── data/                    # Obtención y gestión de datos OHLCV (histórico/tiempo real)
├── indicadores/             # Cálculo de indicadores técnicos
├── estrategia/               # Lógica de evaluación y generación de señales
├── broker/                  # Conexión y ejecución de órdenes (interfaz abstracta + Bitget/Binance)
├── gestion_riesgo/          # Cálculo de tamaño de posición, SL/TP y capital en riesgo
├── notificaciones/          # Alertas (Telegram, Instagram, etc.)
├── utils/                   # Utilidades transversales (logger, decoradores, helpers)
├── logs/                    # Archivos de log generados en ejecución
├── main.py                  # Punto de entrada principal del bot
├── requirements.txt
└── .env
```

---

## 📊 Indicadores Técnicos Implementados

| Indicador | Archivo | Descripción |
|---|---|---|
| **SMA** | `sma.py` | Media Móvil Simple — promedio aritmético de los últimos N cierres. |
| **EMA** | `ema.py` | Media Móvil Exponencial — mayor ponderación a los precios recientes. |
| **RSI** | `rsi.py` | Índice de Fuerza Relativa (suavizado de Wilder) — mide sobrecompra/sobreventa. |
| **ATR** | `atr.py` | Average True Range — mide la volatilidad y calcula el Stop Loss dinámico. |
| **VWAP** | `vwap.py` | Precio Promedio Ponderado por Volumen. |
| **DMI / ADX** | `dm.py` | Directional Movement System (+DI, -DI, ADX) — fuerza y dirección de la tendencia. |

Todos los indicadores están desacoplados de la lógica de conexión: reciben un `DataFrame` de `pandas` con columnas OHLCV y devuelven `Series`/`DataFrame` con los resultados, lo que permite testearlos de forma aislada (`test_indicadores.py`) y reutilizarlos en cualquier estrategia futura.

---

## ⚙️ Configuración

Todos los parámetros del bot se centralizan en [`config.py`](./config.py):

- **Exchange:** `EXCHANGE_ID`, `MARKET_TYPE`, credenciales `API_KEY` / `API_SECRET`.
- **Mercado:** `LISTADO_MONEDAS` (24 pares USDT-M), `TIMEFRAME`, `CANTIDAD_VELAS`.
- **Indicadores:** periodos de RSI, EMA rápida/lenta/tendencia, SMA, ATR, ADX y sus umbrales.
- **Gestión de riesgo:** multiplicadores de ATR para Stop Loss y Take Profit.
- **Runtime:** intervalo de segundos entre ciclos de análisis.

> 🔐 Las API keys se dejan vacías por defecto para permitir el uso exclusivo de datos públicos (sin necesidad de credenciales) durante la fase de pruebas.

---

## 🚀 Instalación y Uso

### Requisitos

- Python 3.11+
- Dependencias: `pandas`, `numpy`, `ccxt`

### Instalación

```bash
git clone https://github.com/<tu-usuario>/RODRI_TRADER_V2.0.git
cd RODRI_TRADER_V2.0
pip install -r requirements.txt
```

### Ejecutar pruebas de indicadores (datos simulados)

```bash
python test_indicadores.py
```

### Ejecutar prueba de conexión real al exchange

```bash
python test_conexion_velas.py
```

Este script se conecta a **Bitget (Mainnet)**, descarga las últimas velas de cada par definido en `config.py`, calcula todos los indicadores y muestra un resumen por consola con el precio actual, EMAs, RSI, ADX y el Stop Loss sugerido.

### Ejecución automática vía GitHub Actions

El workflow [`ejecutar_bot.yml`](./.github/workflows/ejecutar_bot.yml) permite lanzar `test_conexion_velas.py` manualmente desde la pestaña **Actions** de GitHub, sin necesidad de infraestructura propia.

---

## 🗺️ Roadmap

- [x] Estructura inicial del paquete `indicadores/`
- [x] Conexión al exchange vía CCXT y descarga de velas OHLCV
- [x] Scripts de validación de indicadores
- [ ] Módulo `data/` — gestión de datos históricos y en tiempo real
- [ ] Módulo `estrategia/` — clase abstracta + estrategia concreta basada en indicadores
- [ ] Módulo `broker/` — interfaz abstracta + implementación para ejecución de órdenes
- [ ] Módulo `gestion_riesgo/` — cálculo de tamaño de posición y capital en riesgo
- [ ] Módulo `notificaciones/` — alertas automáticas
- [ ] Sistema de logging centralizado (`utils/logger.py`)
- [ ] `main.py` — orquestación completa del bot

---

## 🤝 Contribución

Este es un proyecto de desarrollo personal e incremental. Los cambios se realizan paso a paso, documentando cada fase mediante commits descriptivos.

---

## 📜 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.

---

<div align="center">
<sub>Desarrollado con 🧠 y ☕ por <b>Rodri Trader</b></sub>
</div>