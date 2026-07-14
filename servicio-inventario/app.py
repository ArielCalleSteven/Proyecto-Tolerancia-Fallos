import os

import redis
from flask import Flask, jsonify

app = Flask(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "servicio-bd")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_KEY = "inventario:asientos_disponibles"
DEFAULT_STOCK = 100

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    redis_client.ping()
except Exception as exc:
    redis_client = None
    print(f"[inventario] No se pudo conectar a Redis al iniciar: {exc}")


def obtener_stock():
    if redis_client is None:
        raise ConnectionError("Redis no disponible")

    stock = redis_client.get(REDIS_KEY)
    if stock is None:
        redis_client.set(REDIS_KEY, DEFAULT_STOCK)
        return DEFAULT_STOCK
    return int(stock)


@app.route('/inventario/verificar', methods=['GET'])
def verificar_inventario():
    """Devuelve la cantidad de asientos disponibles desde Redis."""
    try:
        stock = obtener_stock()
    except Exception as exc:
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo consultar el inventario",
            "detalle": str(exc)
        }), 503

    return jsonify({
        "status": "ok",
        "asientos_disponibles": stock
    }), 200


@app.route('/inventario/descontar', methods=['POST'])
def descontar_inventario():
    """Resta un asiento del inventario si hay disponibilidad en Redis."""
    try:
        stock = obtener_stock()
        if stock > 0:
            nuevo_stock = stock - 1
            redis_client.set(REDIS_KEY, nuevo_stock)
            return jsonify({
                "status": "ok",
                "mensaje": "Asiento descontado con éxito",
                "asientos_restantes": nuevo_stock
            }), 200

        return jsonify({
            "status": "error",
            "mensaje": "No hay asientos disponibles"
        }), 400
    except Exception as exc:
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo actualizar el inventario",
            "detalle": str(exc)
        }), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)