# Imagen base ligera de Python 3.11
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y fuerza salida de logs sin buffer
# (para que los print() se vean en tiempo real en los logs de GitHub Actions)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero SOLO requirements.txt para aprovechar la caché de capas de Docker:
# si el código cambia pero no las dependencias, esta capa no se reconstruye
COPY ./Dockerfile/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del proyecto
COPY . .

# Comando por defecto al ejecutar el contenedor
CMD ["python", "test_conexion_velas.py"]