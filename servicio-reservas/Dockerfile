# Usamos una imagen de Python ligera y oficial
FROM python:3.10-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el archivo de requerimientos
COPY requirements.txt .

# Instalamos las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código (el app.py)
COPY . .

# Comando por defecto para encender el servicio
CMD ["python", "app.py"]