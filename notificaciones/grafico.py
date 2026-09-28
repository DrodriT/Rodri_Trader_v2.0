import matplotlib
matplotlib.use("Agg")  # backend sin interfaz gráfica, necesario en GitHub Actions/Docker

import os
import tempfile

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

import config

# Colores usados para cada nivel dibujado en el gráfico.
COLOR_ENTRADA = "#2962FF"
COLOR_SL = "#E53935"
COLOR_TP = "#2E7D32"


def _formatear_par_compacto(par: str) -> str:
    """Convierte 'BTC/USDT:USDT' -> 'BTCUSDT' (misma lógica que telegram_bot.py)."""
    return par.replace("/", "").split(":")[0]


def generar_grafico_operacion(
    df_velas: pd.DataFrame,
    par: str,
    direccion: str,
    riesgo: dict,
    n_velas: int = config.CANTIDAD_VELAS_TENDENCIA,
    timeframe: str = config.TIMEFRAME_TENDENCIA,
) -> str | None:
    """
    Genera un gráfico de velas (candlestick) de las últimas `n_velas`,
    con líneas horizontales punteadas para Entrada, Stop Loss y TP1/TP2/TP3,
    y lo guarda como PNG temporal.

    Por defecto dibuja el timeframe de TENDENCIA (config.TIMEFRAME_TENDENCIA,
    ej. 15m) con config.CANTIDAD_VELAS_TENDENCIA velas: da más contexto
    visual que el timeframe de entrada (5m), aunque los niveles de
    Entrada/SL/TP siguen siendo los calculados sobre el 5m — aquí solo
    cambian las velas de fondo, no el plan de riesgo.

    Requiere que `df_velas` tenga las columnas 'timestamp', 'open', 'high',
    'low', 'close' (las mismas que devuelve descargar_velas() en
    test_conexion_velas.py). No se necesitan los indicadores.

    Devuelve la ruta al archivo PNG generado, o None si no hay datos
    suficientes para dibujar el gráfico O si algo falla al generarlo:
    esta función NUNCA lanza una excepción hacia arriba a propósito, para
    que un fallo al dibujar (ej. velas insuficientes, NaN puntual) no tumbe
    el envío de la alerta entera — telegram_bot.py hace fallback a texto
    plano cuando esto devuelve None.
    """
    if df_velas is None or df_velas.empty or riesgo is None:
        return None

    try:
        df_grafico = df_velas.tail(n_velas).copy()
        df_grafico = df_grafico.set_index("timestamp")
        df_grafico = df_grafico.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
            }
        )[["Open", "High", "Low", "Close"]]

        # Niveles a dibujar: (valor, color, etiqueta)
        niveles = [
            (riesgo["precio_entrada"], COLOR_ENTRADA, "Entrada"),
            (riesgo["stop_loss"], COLOR_SL, "SL"),
            (riesgo["tp1"], COLOR_TP, "TP1"),
            (riesgo["tp2"], COLOR_TP, "TP2"),
            (riesgo["tp3"], COLOR_TP, "TP3"),
        ]

        par_compacto = _formatear_par_compacto(par)
        titulo = f"{par_compacto} {direccion} ({timeframe})"

        fig, ejes = mpf.plot(
            df_grafico,
            type="candle",
            style="charles",
            title=titulo,
            hlines=dict(
                hlines=[nivel[0] for nivel in niveles],
                colors=[nivel[1] for nivel in niveles],
                linestyle="--",
                linewidths=1,
            ),
            volume=False,
            returnfig=True,
            figsize=(9, 5.5),
        )

        # Anotamos cada línea con su etiqueta y precio, dejando un margen extra
        # a la derecha del gráfico para que el texto no choque con los ticks
        # de precio del propio eje (que mplfinance dibuja a la derecha).
        eje_precio = ejes[0]
        x_borde_derecho = len(df_grafico) - 1
        eje_precio.set_xlim(right=x_borde_derecho + max(12, n_velas * 0.2))
        for valor, color, etiqueta in niveles:
            eje_precio.annotate(
                f"{etiqueta}: {valor:,.4f}",
                xy=(x_borde_derecho, valor),
                xytext=(10, 0),
                textcoords="offset points",
                color=color,
                fontsize=8,
                va="center",
                fontweight="bold",
            )

        ruta_temp = os.path.join(tempfile.gettempdir(), f"grafico_{par_compacto}.png")
        fig.savefig(ruta_temp, dpi=130, bbox_inches="tight")
        plt.close(fig)  # liberamos memoria: el bot genera un gráfico por cada par en cada ciclo

        return ruta_temp

    except Exception as e:
        print(f"  ❌ Error generando el gráfico de {par}: {type(e).__name__} - {e}")
        plt.close("all")  # por si la figura quedó a medio crear, no se acumula en memoria
        return None
    
def generar_grafico_semanal(
    capitales: list[float],
    indice_inicio_semana: int,
    etiquetas_dias: list[str],
    pnl_dias: list[float],
    capital_inicial: float,
) -> str | None:
    """
    Genera la imagen del informe semanal con dos paneles:
      - Arriba: curva de capital operación a operación desde el inicio del
        test, con una línea vertical donde empieza la semana.
      - Abajo: PnL de cada día de la semana (verde si gana, rojo si pierde).

    Devuelve la ruta del PNG temporal, o None si algo falla (nunca lanza
    excepción: el informe de texto se envía igualmente).
    """
    try:
        fig, (eje_capital, eje_dias) = plt.subplots(
            2, 1, figsize=(9, 7), gridspec_kw={"height_ratios": [3, 2]}
        )

        x = list(range(len(capitales)))
        eje_capital.plot(x, capitales, color=COLOR_ENTRADA, linewidth=1.6)
        eje_capital.axhline(capital_inicial, color="#9E9E9E", linestyle="--", linewidth=1)
        eje_capital.fill_between(
            x, capital_inicial, capitales,
            where=[c >= capital_inicial for c in capitales],
            color=COLOR_TP, alpha=0.15, interpolate=True,
        )
        eje_capital.fill_between(
            x, capital_inicial, capitales,
            where=[c < capital_inicial for c in capitales],
            color=COLOR_SL, alpha=0.15, interpolate=True,
        )
        if 0 < indice_inicio_semana < len(capitales):
            eje_capital.axvline(indice_inicio_semana, color="#FB8C00", linestyle=":", linewidth=1.3)
            eje_capital.annotate(
                "inicio de semana", xy=(indice_inicio_semana, capitales[indice_inicio_semana]),
                xytext=(5, 10), textcoords="offset points", color="#FB8C00", fontsize=8,
            )
        eje_capital.set_title("Evolución del capital (USDT)")
        eje_capital.set_xlabel("Operaciones cerradas")
        eje_capital.grid(alpha=0.3)

        colores = [COLOR_TP if v >= 0 else COLOR_SL for v in pnl_dias]
        eje_dias.bar(etiquetas_dias, pnl_dias, color=colores)
        eje_dias.axhline(0, color="#9E9E9E", linewidth=1)
        eje_dias.set_title("PnL por día (USDT)")
        eje_dias.grid(axis="y", alpha=0.3)

        fig.tight_layout()
        ruta_temp = os.path.join(tempfile.gettempdir(), "grafico_semanal.png")
        fig.savefig(ruta_temp, dpi=130, bbox_inches="tight")
        plt.close(fig)
        return ruta_temp

    except Exception as e:
        print(f"  ❌ Error generando el gráfico semanal: {type(e).__name__} - {e}")
        plt.close("all")
        return None