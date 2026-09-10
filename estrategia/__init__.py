"""
Paquete de estrategia: implementa el 'Algorithmic Entry Model V1.0'.

Expone una única función pública (generar_senal) que orquesta internamente
el HTF Filter, el Mandatory Filter y el cálculo del Score (0-100), de forma
que el resto del proyecto (test_conexion_velas.py, futuros scripts) solo
necesita importar esta función sin conocer los detalles internos del modelo.
"""

from .entry_signal import generar_senal

__all__ = ["generar_senal"]