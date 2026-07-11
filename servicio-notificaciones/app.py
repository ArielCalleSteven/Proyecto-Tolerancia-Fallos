from flask import Flask, jsonify
import time

app = Flask(__name__)

@app.route('/notificaciones/enviar', methods=['POST'])
def enviar_correo():
    # Simulamos un pequeño retraso de red al enviar un correo (200ms)
    time.sleep(0.2)
    return jsonify({
        "status": "ok",
        "mensaje": "Correo de confirmación enviado exitosamente al usuario"
    }), 200

if __name__ == '__main__':
    # El servicio de notificaciones correrá en el puerto 5004
    app.run(host='0.0.0.0', port=5004)