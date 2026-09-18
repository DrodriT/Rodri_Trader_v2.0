import matplotlib
matplotlib.use("Agg")  # backend sin interfaz gráfica, necesario en GitHub Actions/Docker

import os
import tempfile

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

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
    n_velas: int = 60,
) -> str | None:
    """
    Genera un gráfico de velas (candlestick) de las últimas `n_velas`,
    con líneas horizontales punteadas para Entrada, Stop Loss y TP1/TP2/TP3,
    y lo guarda como PNG temporal.

    Requiere que `df_velas` tenga las columnas 'timestamp', 'open', 'high',
    'low', 'close' (las mismas que devuelve descargar_velas() en
    test_conexion_velas.py). No se necesitan los indicadores.

    Devuelve la ruta al archivo PNG generado, o None si no hay datos
    suficientes para dibujar el gráfico.
    """
    if df_velas is None or df_velas.empty or riesgo is None:
        return None

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
    titulo = f"{par_compacto} {direccion}"

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