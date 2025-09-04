from flask import Flask, render_template, request, jsonify
from interactor import ESP32Interactor

app = Flask(__name__)
esp = ESP32Interactor("192.168.137.230")

DEVICE_PINS = {
    "light": 13,
    "fan": 14,
    "door": 27
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control", methods=["POST"])
def control():
    data = request.get_json()
    device = data["device"]
    state = int(data["state"])
    pin = DEVICE_PINS.get(device)
    
    if pin is not None:
        try:
            esp.set_pin_state(pin, state)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": False, "error": "Invalid device"})

@app.route("/status")
def status():
    try:
        pin_states = esp.get_all_pin_states()
        result = {
            device: pin_states.get(pin, 0)
            for device, pin in DEVICE_PINS.items()
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({dev: -1 for dev in DEVICE_PINS}, error=str(e))

if __name__ == "__main__":
    app.run(debug=True, port=5000)


# def web_server():
#     app.run(debug=True, port=5000)