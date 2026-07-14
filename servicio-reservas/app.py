import json
import os

import redis
import requests
from flask import Flask, jsonify

app = Flask(__name__)

# URLs preparadas para la red interna de Kubernetes
URL_INVENTARIO = "http://inventario-service:5002/inventario/descontar"
URL_PAGOS = "http://pagos-service:5003/pagos/procesar"
URL_NOTIFICACIONES = "http://notificaciones-service:5004/notificaciones/enviar"

REDIS_HOST = os.environ.get("REDIS_HOST", "servicio-bd")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_KEY = "reservas:registros"

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    redis_client.ping()
except Exception as exc:
    redis_client = None
    print(f"[reservas] No se pudo conectar a Redis al iniciar: {exc}")


def registrar_reserva(reserva_payload):
    if redis_client is None:
        raise ConnectionError("Redis no disponible")

    redis_client.lpush(REDIS_KEY, json.dumps(reserva_payload))
    return True


@app.route('/reservas/comprar', methods=['POST'])
def comprar_entrada():
    # --- PASO 1: DESCONTAR INVENTARIO ---
    try:
        resp_inventario = requests.post(URL_INVENTARIO, timeout=2.0)
        if resp_inventario.status_code != 200:
            return jsonify({"status": "error", "mensaje": "No hay asientos disponibles"}), 400
    except Exception as exc:
        return jsonify({"status": "error", "mensaje": "Fallo crítico en Inventario", "detalle": str(exc)}), 500

    # --- PASO 2: PROCESAR PAGO (DEFENSA CONTRA FALLO A - "La Pasarela Lenta") ---
    try:
        resp_pago = requests.post(URL_PAGOS, timeout=2.0)
        if resp_pago.status_code != 200:
            return jsonify({"status": "error", "mensaje": "Error en la pasarela de pagos"}), 500
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "pendiente",
            "mensaje": "Pasarela saturada. Tu asiento está reservado, el cobro está en cola y se procesará en breve."
        }), 202
    except Exception as exc:
        return jsonify({"status": "error", "mensaje": "Fallo crítico en Pagos", "detalle": str(exc)}), 500

    # --- PASO 3: ENVIAR NOTIFICACIÓN (DEFENSA CONTRA FALLO C - "El Correo Perdido") ---
    estado_correo = "Enviado"
    try:
        requests.post(URL_NOTIFICACIONES, timeout=1.0)
    except Exception as exc:
        estado_correo = "Pendiente (Servicio caído. Se enviará más tarde)"
        print(f"[LOG DE AUDITORÍA] Fallo en notificaciones: {exc}")

    # --- PASO 4: REGISTRAR RESERVA EN REDIS ---
    try:
        reserva_payload = {
            "status": "ok",
            "estado_notificacion": estado_correo
        }
        registrar_reserva(reserva_payload)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo persistir la reserva",
            "detalle": str(exc)
        }), 503

    return jsonify({
        "status": "ok",
        "mensaje": "¡Compra realizada con éxito!",
        "estado_notificacion": estado_correo
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)