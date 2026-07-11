from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# URLs preparadas para la red interna de Kubernetes
URL_INVENTARIO = "http://inventario-service:5002/inventario/descontar"
URL_PAGOS = "http://pagos-service:5003/pagos/procesar"
URL_NOTIFICACIONES = "http://notificaciones-service:5004/notificaciones/enviar"


@app.route('/reservas/comprar', methods=['POST'])
def comprar_entrada():
    # --- PASO 1: DESCONTAR INVENTARIO ---
    try:
        resp_inventario = requests.post(URL_INVENTARIO)
        if resp_inventario.status_code != 200:
            return jsonify({"status": "error", "mensaje": "No hay asientos disponibles"}), 400
    except Exception as e:
        return jsonify({"status": "error", "mensaje": "Fallo crítico en Inventario"}), 500

    # --- PASO 2: PROCESAR PAGO (DEFENSA CONTRA FALLO A - "La Pasarela Lenta") ---
    # Implementamos un Fallback con Timeout (versión simplificada de Circuit Breaker)
    # Si el pago tarda más de 2 segundos, abortamos la conexión para no colgar el sistema.
    try:
        resp_pago = requests.post(URL_PAGOS, timeout=2.0)
        if resp_pago.status_code != 200:
            return jsonify({"status": "error", "mensaje": "Error en la pasarela de pagos"}), 500
    except requests.exceptions.Timeout:
        # FALLBACK: En lugar de colapsar, damos una respuesta controlada
        return jsonify({
            "status": "pendiente",
            "mensaje": "Pasarela saturada. Tu asiento está reservado, el cobro está en cola y se procesará en breve."
        }), 202

    # --- PASO 3: ENVIAR NOTIFICACIÓN (DEFENSA CONTRA FALLO C - "El Correo Perdido") ---
    # Implementamos Degradación Elegante. Si las notificaciones fallan, la compra IGUAL es exitosa.
    estado_correo = "Enviado"
    try:
        # Un timeout cortito, si no responde rápido, seguimos de largo
        requests.post(URL_NOTIFICACIONES, timeout=1.0)
    except Exception as e:
        estado_correo = "Pendiente (Servicio caído. Se enviará más tarde)"
        print(f"[LOG DE AUDITORÍA] Fallo en notificaciones: {e}")

    # --- RESPUESTA EXITOSA FINAL ---
    return jsonify({
        "status": "ok",
        "mensaje": "¡Compra realizada con éxito!",
        "estado_notificacion": estado_correo
    }), 200

if __name__ == '__main__':
    # El servicio de reservas correrá en el puerto 5001
    app.run(host='0.0.0.0', port=5001)