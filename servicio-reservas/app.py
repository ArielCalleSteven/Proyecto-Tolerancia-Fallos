import json
import os
import redis
import requests
from flask import Flask, jsonify
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

app = Flask(__name__)

# URLs preparadas para la red interna de Kubernetes
URL_INVENTARIO = "http://inventario-service:5002/inventario/descontar"
URL_PAGOS = "http://pagos-service:5003/pagos/procesar"
URL_NOTIFICACIONES = "http://notificaciones-service:5004/notificaciones/enviar"

REDIS_HOST = os.environ.get("REDIS_HOST", "servicio-bd")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_KEY = "reservas:registros"

def obtener_conexion_redis():
    """Crea la conexión a Redis bajo demanda para soportar desconexiones"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# --- DEFENSA CONTRA FALLO D: "Base de Datos Intermitente" ---
# Patrón: Retries con Exponential Backoff
# Si Redis falla, reintenta hasta 4 veces, esperando 1s, luego 2s, luego 4s...
@retry(
    stop=stop_after_attempt(4), 
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((redis.exceptions.ConnectionError, redis.exceptions.TimeoutError))
)
def registrar_reserva(reserva_payload):
    cliente_redis = obtener_conexion_redis()
    cliente_redis.ping() # Forzamos a ver si está vivo
    cliente_redis.lpush(REDIS_KEY, json.dumps(reserva_payload))
    return True

# --- DEFENSA CONTRA FALLO A: "El Inventario Fantasma" ---
# Patrón: Retry Automático
# Si el pod de Inventario se está reiniciando, le damos 3 oportunidades antes de rendirnos
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def llamar_inventario_con_reintentos():
    resp = requests.post(URL_INVENTARIO, timeout=3.0)
    resp.raise_for_status() # Si no es 200, lanza error y obliga a reintentar
    return resp


@app.route('/reservas/comprar', methods=['POST'])
def comprar_entrada():
    # --- PASO 1: DESCONTAR INVENTARIO (Ahora con Retries) ---
    try:
        llamar_inventario_con_reintentos()
    except Exception as exc:
        return jsonify({"status": "error", "mensaje": "Fallo crítico en Inventario. Intente más tarde.", "detalle": str(exc)}), 503

    # --- PASO 2: PROCESAR PAGO (Tu defensa original - Circuit Breaker/Fallback) ---
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

    # --- PASO 3: ENVIAR NOTIFICACIÓN (Tu defensa original - Correo Perdido) ---
    estado_correo = "Enviado"
    try:
        resp_notif = requests.post(URL_NOTIFICACIONES, timeout=1.0)
        resp_notif.raise_for_status() 
    except Exception as exc:
        estado_correo = "Pendiente (Servicio caído. Se enviará más tarde)"
        print(f"[LOG DE AUDITORÍA] Fallo en notificaciones: {exc}")

    # --- PASO 4: REGISTRAR RESERVA EN REDIS (Ahora con Exponential Backoff) ---
    try:
        reserva_payload = {
            "status": "ok",
            "estado_notificacion": estado_correo
        }
        registrar_reserva(reserva_payload)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo persistir la reserva tras múltiples intentos",
            "detalle": str(exc)
        }), 503

    return jsonify({
        "status": "ok",
        "mensaje": "¡Compra realizada con éxito!",
        "estado_notificacion": estado_correo
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)