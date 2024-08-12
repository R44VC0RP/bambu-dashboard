from flask import Flask, jsonify, render_template, request
from redis_handler import RedisHandler
import xmlrpc.client

app = Flask(__name__)
redis_handler = RedisHandler()

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(redis_handler.get_printer_status())

@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify(redis_handler.get_printer_progress())

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET'])
def get_config():
    return render_template('config.html')

@app.route('/config_get', methods=['GET'])
def get_config_get():
    config = redis_handler.get_config()
    printers = redis_handler.get_printers()
    
    response = {
        'smtp': config.get('smtp', {}),
        'printers': printers
    }
    
    return jsonify(response)

@app.route('/config/printers/check', methods=['POST'])
def check_printers():
    data = request.form
    ip = data.get('ip')
    access_code = data.get('accessCode')
    serial_number = data.get('serialNumber')
    return jsonify({"status" : check_MQTT_connection(ip, access_code, serial_number)})

@app.route('/config/update/email', methods=['POST'])
def update_email():
    data = request.form
    smtp_server = data.get('smtpServer')
    smtp_port = data.get('smtpPort')
    smtp_username = data.get('smtpUser')
    smtp_password = data.get('smtpPass')
    sendFrom = data.get('sendFrom')
    sendTo = data.get('sendTo')

    config = {
        'smtpserver': smtp_server,
        'smtpport': smtp_port,
        'smtpuser': smtp_username,
        'smtppass': smtp_password,
        'sendfrom': sendFrom,
        'sendto': sendTo
    }

    redis_handler.set_config(config)

    return jsonify({"message": "Email configuration updated successfully"})

@app.route('/config/get/email', methods=['GET'])
def get_email_config():
    config = redis_handler.get_config()
    return jsonify(config)

@app.route('/config/printers/add', methods=['POST'])
def add_printer():
    data = request.form
    printer_name = data.get('printerName')
    ip = data.get('printerIP')
    access_code = data.get('accessCode')
    serial_number = data.get('serialNumber')
    
    # Check for conflicts
    printers = redis_handler.get_printers()
    for existing_name, existing_printer in printers.items():
        if existing_name == printer_name:
            return jsonify({"status": "error", "message": "Printer name already exists"})
        if existing_printer["ip"] == ip:
            return jsonify({"status": "error", "message": "IP address already in use"})
        if existing_printer["access_code"] == access_code:
            return jsonify({"status": "error", "message": "Access code already in use"})
        if existing_printer["serial_number"] == serial_number:
            return jsonify({"status": "error", "message": "Serial number already in use"})
    
    if not check_MQTT_connection(ip, access_code, serial_number):
        return jsonify({"status": "error", "message": "Printer is not connected"})
    
    # If no conflicts, add the new printer
    printers[printer_name] = {"ip": ip, "access_code": access_code, "serial_number": serial_number}
    redis_handler.set_printers(printers)

    return jsonify({"status" : "success"})

@app.route('/config/printers/delete', methods=['POST'])
def delete_printer():
    data = request.form
    printer_name = data.get('printer_name')
    printers = redis_handler.get_printers()
    if printer_name in printers:
        del printers[printer_name]
        redis_handler.set_printers(printers)
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Printer not found"})

@app.route('/restart_mqtt', methods=['POST'])
def restart_mqtt():
    try:
        server = xmlrpc.client.ServerProxy('http://localhost:9001/RPC2')
        server.supervisor.stopProcess('mqtt_client')
        server.supervisor.startProcess('mqtt_client')
        return jsonify({"status": "success", "message": "MQTT client restarted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def start_flask_app():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    start_flask_app()