from flask import Flask, jsonify, request

app = Flask(__name__)

# Simulamos una pequeña base de datos en memoria para el inventario
inventario_db = {
    "asientos_disponibles": 100
}

@app.route('/inventario/verificar', methods=['GET'])
def verificar_inventario():
    """Devuelve la cantidad de asientos disponibles."""
    return jsonify({
        "status": "ok",
        "asientos_disponibles": inventario_db["asientos_disponibles"]
    }), 200

@app.route('/inventario/descontar', methods=['POST'])
def descontar_inventario():
    """Resta un asiento del inventario si hay disponibilidad."""
    if inventario_db["asientos_disponibles"] > 0:
        inventario_db["asientos_disponibles"] -= 1
        return jsonify({
            "status": "ok",
            "mensaje": "Asiento descontado con éxito",
            "asientos_restantes": inventario_db["asientos_disponibles"]
        }), 200
    else:
        return jsonify({
            "status": "error",
            "mensaje": "No hay asientos disponibles"
        }), 400

if __name__ == '__main__':
    # El servicio correrá en el puerto 5002
    app.run(host='0.0.0.0', port=5002)