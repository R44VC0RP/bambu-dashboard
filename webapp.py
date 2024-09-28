import json
import time
import signal
import sys
import threading
import email_send
from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import os
import subprocess
from pymongo import MongoClient
from dotenv import load_dotenv
import atexit
import requests

app = Flask(__name__)


def start_mgmtapp():
    subprocess.run(['screen', '-dmS', 'mgmtapp', 'python', 'mgmtapp.py'])

# Function to stop mgmtapp.py file then screen session
def stop_mgmtapp():
    try:
        response = requests.post('http://localhost:3434/shutdown')
        if response.status_code == 200:
            print("mgmtapp.py shutting down gracefully...")
        else:
            print(f"Failed to shutdown mgmtapp.py. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error sending shutdown request to mgmtapp.py: {str(e)}")
    
    # Wait a bit for the server to shut down

    time.sleep(2)
    
    # If the server is still running, force kill it
    subprocess.run(['pkill', '-f', 'mgmtapp.py'])
    subprocess.run(['screen', '-S', 'mgmtapp', '-X', 'quit'])

# Function to restart mgmtapp.py screen session
def restart_mgmtapp():
    stop_mgmtapp()
    start_mgmtapp()

# Function to check if mgmtapp.py is running
def is_mgmtapp_running():
    result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
    return 'mgmtapp' in result.stdout



# Load environment variables
load_dotenv()
mongo_uri = os.getenv('MONGO_URI')  # Ensure you have WEBAPP_MONGO_URI in your .env
client = MongoClient(mongo_uri)
db = client['bambu_dashboard']
smtp_config_collection = db['smtp_credentials']
printer_list_collection = db['printers']

# Initialize collections if they don't exist
if 'smtp_credentials' not in db.list_collection_names():
    smtp_config_collection.insert_one({
        "smtpserver": "",
        "smtpport": "",
        "smtpuser": "",
        "smtppass": "",
        "sendfrom": "",
        "sendto": ""
    })

if 'printers' not in db.list_collection_names():
    # Initialize with an empty list instead of an empty printer
    pass  # No need to insert an empty printer

if 'motor_endpoints' not in db.list_collection_names():
    db.create_collection('motor_endpoints')

motor_endpoints_collection = db['motor_endpoints']

# MongoDB Functions

def get_smtp_config():
    return smtp_config_collection.find_one({}, {'_id': 0})

def update_smtp_config(new_config):
    smtp_config_collection.update_one({}, {"$set": new_config}, upsert=True)

def get_printer_list():
    return list(printer_list_collection.find({}, {'_id': 0}))

def add_printer_to_db(printer_data):
    printer_list_collection.insert_one(printer_data)

def delete_printer_from_db(printer_name):
    printer_list_collection.delete_one({"name": printer_name})

def update_printer_in_db(name, new_data):
    printer_list_collection.update_one({"name": name}, {"$set": new_data})

def get_sending_creds():
    return smtp_config_collection.find_one({}, {'_id': 0})

def get_motor_endpoints():
    return list(motor_endpoints_collection.find({}, {'_id': 0}))

def add_motor_endpoint(endpoint_data):
    motor_endpoints_collection.insert_one(endpoint_data)

def delete_motor_endpoint(printer_name, module_name):
    motor_endpoints_collection.delete_one({"printer_name": printer_name, "module_name": module_name})

# Initialize authentication
auth = HTTPBasicAuth()

# User data for authentication
users = {
    "admin": generate_password_hash("ravonxaccess")  # Replace "admin" with a secure password
} 

@app.route('/mgmtapp/status', methods=['GET'])
@auth.login_required
def mgmtapp_status():
    status = "running" if is_mgmtapp_running() else "stopped"
    return jsonify({"status": status})

@app.route('/mgmtapp/restart', methods=['POST'])
@auth.login_required
def mgmtapp_restart():
    restart_mgmtapp()
    return jsonify({"status": "success"})

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@app.route('/status', methods=['GET'])
def get_status():
    # Assuming this endpoint is managed by mgmtapp.py
    # If not, you might need to implement synchronization with mgmtapp.py
    # For now, returning an empty dictionary or could integrate with mgmtapp.py's data
    return jsonify({})  # Placeholder

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET'])
@auth.login_required
def config():
    return render_template('config.html')

@app.route('/config_get', methods=['GET'])
def get_config_get():
    smtp_config = get_smtp_config()
    printers = get_printer_list()
    motor_endpoints = get_motor_endpoints()

    response = {
        'smtp': smtp_config,
        'printers': printers,
        'motor_endpoints': motor_endpoints
    }
    
    return jsonify(response)

@app.route('/config/update/email', methods=['POST'])
@auth.login_required
def update_email():
    data = request.form
    smtp_server = data.get('smtpServer')
    smtp_port = data.get('smtpPort')
    smtp_username = data.get('smtpUser')
    smtp_password = data.get('smtpPass')
    sendFrom = data.get('sendFrom')
    sendTo = data.get('sendTo')

    new_config = {
        'smtpserver': smtp_server,
        'smtpport': smtp_port,
        'smtpuser': smtp_username,
        'smtppass': smtp_password,
        'sendfrom': sendFrom,
        'sendto': sendTo
    }

    update_smtp_config(new_config)

    return jsonify({"message": "Email configuration updated successfully"})

@app.route('/config/get/email', methods=['GET'])
def get_email_config():
    return jsonify(get_smtp_config())

@app.route('/config/printers/add', methods=['POST'])
@auth.login_required
def add_printer():
    data = request.form
    printer_name = data.get('printerName')
    ip = data.get('printerIP')
    access_code = data.get('accessCode')
    serial_number = data.get('serialNumber')

    # Check for conflicts in MongoDB
    existing_printer = printer_list_collection.find_one({"$or": [
        {"name": printer_name},
        {"ip": ip},
        {"access_code": access_code},
        {"serial_number": serial_number}
    ]})
    
    if existing_printer:
        if existing_printer.get("name") == printer_name:
            return jsonify({"status": "error", "message": "Printer name already exists"})
        if existing_printer.get("ip") == ip:
            return jsonify({"status": "error", "message": "IP address already in use"})
        if existing_printer.get("access_code") == access_code:
            return jsonify({"status": "error", "message": "Access code already in use"})
        if existing_printer.get("serial_number") == serial_number:
            return jsonify({"status": "error", "message": "Serial number already in use"})
    
    # Add the new printer to MongoDB
    printer_data = {
        "name": printer_name,
        "ip": ip,
        "access_code": access_code,
        "serial_number": serial_number
    }
    add_printer_to_db(printer_data)

    return jsonify({"status" : "success"})

@app.route('/config/printers/delete', methods=['POST'])
@auth.login_required
def delete_printer():
    data = request.json
    printer_name = data.get('printer_name')
    print(f"Attempting to delete printer: {printer_name}")
    
    delete_printer_from_db(printer_name)
    
    return jsonify({"status": "success"})

@app.route('/config/motor_endpoints/add', methods=['POST'])
@auth.login_required
def add_motor_endpoint_route():
    data = request.form
    printer_name = data.get('printerName')
    module_name = data.get('moduleName')
    access_code = data.get('accessCode')
    endpoint = data.get('endpoint')

    # Check for conflicts in MongoDB
    existing_endpoint = motor_endpoints_collection.find_one({
        "printer_name": printer_name,
        "module_name": module_name
    })
    
    if existing_endpoint:
        return jsonify({"status": "error", "message": "Motor endpoint already exists for this printer and module"})
    
    # Add the new motor endpoint to MongoDB
    endpoint_data = {
        "printer_name": printer_name,
        "module_name": module_name,
        "access_code": access_code,
        "endpoint": endpoint
    }
    add_motor_endpoint(endpoint_data)

    return jsonify({"status": "success"})

@app.route('/config/motor_endpoints/delete', methods=['POST'])
@auth.login_required
def delete_motor_endpoint_route():
    data = request.json
    printer_name = data.get('printer_name')
    module_name = data.get('module_name')
    
    delete_motor_endpoint(printer_name, module_name)
    
    return jsonify({"status": "success"})

# Ensure no duplicate route definitions below

def cleanup():
    print("Cleaning up...")
    stop_mgmtapp()

def signal_handler(signum, frame):
    print(f"Received signal {signum}")
    cleanup()
    sys.exit(0)

# Register the cleanup function to be called on normal program termination
atexit.register(cleanup)

# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    try:
        if os.uname().nodename == 'ExonAir.local':
            start_mgmtapp()
            app.run(host='0.0.0.0', port=4300)
        else:
            app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        cleanup()