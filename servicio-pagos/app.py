from flask import Flask, jsonify, request
import time
import random

app = Flask(__name__)

# Variable global para controlar si el sistema está "sano" o "fallando"
caos_activo = False

@app.route('/pagos/procesar', methods=['POST'])
def procesar_pago():
    global caos_activo
    
    # 💥 FASE DE CAOS: Si está activo, tardamos 20 segundos
    if caos_activo:
        print("[CAOS ACTIVADO] La pasarela está lenta. Esperando 20 segundos...")
        time.sleep(20)
        return jsonify({
            "status": "error", 
            "mensaje": "Timeout: La pasarela de pagos no responde"
        }), 503
    
    # ✅ FASE NORMAL: El pago es rápido y exitoso
    # Simulamos un tiempo de procesamiento normal y aleatorio (entre 100ms y 300ms)
    time.sleep(random.uniform(0.1, 0.3))
    return jsonify({
        "status": "ok", 
        "mensaje": "Pago procesado correctamente",
        "transaccion_id": random.randint(10000, 99999)
    }), 200

# Endpoint "secreto" para encender o apagar la lentitud durante la Demo en vivo
@app.route('/admin/caos/pagos/toggle', methods=['POST'])
def toggle_caos():
    global caos_activo
    caos_activo = not caos_activo # Invierte el estado actual
    
    estado = "LENTO (Fallo activado)" if caos_activo else "RÁPIDO (Normalidad)"
    return jsonify({
        "status": "ok", 
        "mensaje": f"Estado de la pasarela cambiado a: {estado}"
    }), 200

if __name__ == '__main__':
    # El servicio de pagos correrá en el puerto 5003
    app.run(host='0.0.0.0', port=5003)