from bpm.bambuconfig import BambuConfig
from bpm.bambuprinter import BambuPrinter
from bpm.bambutools import PrinterState, parseStage, parseFan
import json
import time
import signal
import sys
import threading
import email_send
from flask import Flask, jsonify, render_template, request
import os
import configparser

app = Flask(__name__)


global printer_status
printer_status = {}
global printers_progress
printers_progress = {}

config_file_path = 'config.ini'
# create config.ini if it doesn't exist
if not os.path.exists(config_file_path):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {}
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

printers_json_file = "printers.json"

global printers_json
printers_json = {}

def restart_program():
    """Restarts the current program."""
    print("Restarting the program...")
    python = sys.executable
    os.execl(python, python, *sys.argv)


def write_printers_json():
    global printers_json
    with open(printers_json_file, 'w') as json_file:
        json.dump(printers_json, json_file, indent=4)

def read_printers_json():
    global printers_json
    if not os.path.exists(printers_json_file):
        printers_json = {}
        write_printers_json()
    else:
        with open(printers_json_file, 'r') as json_file:
            printers_json = json.load(json_file)

@app.route('/status', methods=['GET'])
def get_status():
    global printer_status
    return jsonify(printer_status)


@app.route('/progress', methods=['GET'])
def get_progress():
    global printers_progress
    return jsonify(printers_progress)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET'])
def get_config():
    return render_template('config.html')

@app.route('/config_get', methods=['GET'])
def get_config_get():
    config = configparser.ConfigParser()
    config.read(config_file_path)
    smtp_config = dict(config['DEFAULT'])
    
    global printers_json
    
    response = {
        'smtp': smtp_config,
        'printers': printers_json
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

    config = configparser.ConfigParser()
    config.read(config_file_path)

    if 'DEFAULT' not in config:
        config['DEFAULT'] = {}

    config['DEFAULT']['smtpserver'] = smtp_server
    config['DEFAULT']['smtpport'] = smtp_port
    config['DEFAULT']['smtpuser'] = smtp_username
    config['DEFAULT']['smtppass'] = smtp_password
    config['DEFAULT']['sendfrom'] = sendFrom
    config['DEFAULT']['sendto'] = sendTo

    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

    return jsonify({"message": "Email configuration updated successfully"})

@app.route('/config/get/email', methods=['GET'])
def get_email_config():
    config = configparser.ConfigParser()
    config.read(config_file_path)
    return jsonify(config['DEFAULT'])

@app.route('/config/printers/add', methods=['POST'])
def add_printer():
    data = request.form
    printer_name = data.get('printerName')
    ip = data.get('printerIP')
    access_code = data.get('accessCode')
    serial_number = data.get('serialNumber')
    read_printers_json()
    
    # Check for conflicts
    for existing_name, existing_printer in printers_json.items():
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
    printers_json[printer_name] = {"ip": ip, "access_code": access_code, "serial_number": serial_number}
    write_printers_json()

    return jsonify({"status" : "success"})

@app.route('/config/printers/delete', methods=['POST'])
def delete_printer():
    data = request.form
    printer_name = data.get('printer_name')
    read_printers_json()
    if printer_name in printers_json:
        del printers_json[printer_name]
        write_printers_json()
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Printer not found"})

def start_flask_app():
    app.run(host='0.0.0.0', port=5000)



def update_printer_status(name, status):
    global printer_status
    printer_status[name] = status
    
    # Update the local JSON file
    with open('printer_status.json', 'w') as f:
        json.dump(printer_status, f, indent=4)
    
def poopGenerated(printer):
    print("Poop Generated by " + printer.name)

def printerStateChange(name, old_state, new_state):
    print(f"{name} - State changed from {old_state} to {new_state}")
    if new_state == "printing":
        email_send.send_email(name, "Print Job Started")
    elif new_state == "idle":
        email_send.send_email(name, "Print Job Completed")

def format_time(minutes):
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m"

def get_stage_info(stage):
    stages = {
        -1: "Idle",
        0: "Printing",
        1: "Auto Bed Leveling",
        2: "Heatbed Preheating",
        3: "Sweeping XY Mech Mode",
        4: "Changing Filament",
        5: "M400 Pause",
        6: "Paused due to filament runout",
        7: "Heating Hotend",
        8: "Calibrating Extrusion",
        9: "Scanning Bed Surface",
        10: "Inspecting First Layer",
        11: "Identifying Build Plate Type",
        12: "Calibrating Micro Lidar",
        13: "Homing Toolhead",
        14: "Cleaning Nozzle Tip",
        15: "Checking Extruder Temperature",
        16: "Printing was paused by the user",
        17: "Pause of front cover falling",
        18: "Calibrating Micro Lidar",
        19: "Calibrating Extrusion Flow",
        20: "Paused due to nozzle temperature malfunction",
        21: "Paused due to heat bed temperature malfunction",
        22: "Filament unloading",
        23: "Skip step pause",
        24: "Filament loading",
        25: "Motor noise calibration",
        26: "Paused due to AMS lost",
        27: "Paused due to low speed of the heat break fan",
        28: "Paused due to chamber temperature control error",
        29: "Cooling chamber",
        30: "Paused by the Gcode inserted by user",
        31: "Motor noise showoff",
        32: "Nozzle filament covered detected pause",
        33: "Cutter error pause",
        34: "First layer error pause",
        35: "Nozzle clog pause",
        255: "Printer is idle"
    }
    return stages.get(stage, "Unknown stage")


def create_printer(ip, access_code, serial_number, printer_name):
    config = BambuConfig(hostname=ip, access_code=access_code, serial_number=serial_number)
    printer = BambuPrinter(config=config)
    printer.name = printer_name
    return printer

def monitor_printer(printer):
    printer.start_session()
    
    # Wait for the printer to connect and receive initial data
    time.sleep(3)
    
    # Print current printer status
    update_printer_status(printer.name, is_printer_idle(printer))
    active_printers = ""
    for printer in printers:
        active_printers += printer.name + ", "
    print(f"Active Printers: {active_printers}")

    old_state = "idle" if is_printer_idle(printer) else "printing"
    while True:

        #print(f"{printer.name} - Old Stage: {get_stage_info(printer._current_stage)}")
        current_state = "idle" if is_printer_idle(printer) else "printing"

        # This is updating the global progress variable that can be accessed by the Flask app
        if printer.name not in printers_progress:
            printers_progress[printer.name] = {}
        
        printers_progress[printer.name]["stage"] = get_stage_info(printer._current_stage)
        printers_progress[printer.name]["progress"] = str(printer.percent_complete) + "%"
        printers_progress[printer.name]["time_remaining"] = format_time(printer.time_remaining)
        printers_progress[printer.name]["current_state"] = current_state
        
        # Serialize the printer object to JSON and then parse it back to a dictionary
        printer_json_str = json.dumps(printer, default=printer.jsonSerializer, indent=4, sort_keys=True)
        printers_progress[printer.name]["doc"] = json.loads(printer_json_str)

        if current_state != old_state:
            printerStateChange(printer.name, old_state, current_state)
            old_state = current_state
        
        if current_state == "printing":
            if printer._current_stage == 14:
                poopGenerated(printer)
            print(f"{printer.name} - Print Progress: {printer.percent_complete}% | Current Stage: {get_stage_info(printer._current_stage)}")
        
        else:
            print(f"{printer.name} - Printer is idle")
        time.sleep(5)
    
    # Print complete
    print(f"{printer.name} - Print job finished!")
    
    # Serialize printer state to JSON
    printer_json = json.dumps(printer, default=printer.jsonSerializer, indent=4, sort_keys=True)
    print(f"{printer.name} - Printer State JSON:")
    #print(printer_json)
    
    # End the session
    printer.quit()

def is_printer_idle(printer):
    gcode_state = printer._gcode_state
    print_type = printer._print_type
    current_stage = printer._current_stage
    #print(f"{printer.name} - Gcode State: {gcode_state} | Print Type: {print_type} | Current Stage: {current_stage}")
    if gcode_state == "FINISH" and print_type == "idle" and current_stage == 255:
        return True
    else:
        return False

printers = []

def signal_handler(sig, frame):
    print("Keyboard interrupt received. Closing all sessions...")
    global printers
    for printer in printers:
        printer.quit()
    sys.exit(0)

def check_MQTT_connection(ip, access_code, serial_number):
    try:
        config = BambuConfig(hostname=ip, access_code=access_code, serial_number=serial_number)
        printer = BambuPrinter(config=config)
        printer.start_session()
        return True
    except Exception as e:
        print(f"Error checking MQTT connection: {e}")
        return False

def restart_main():
    print("Restarting main function")
    global printers
    global printer_status
    global printers_progress

    # Clear the current printer status
    printer_status = {}
    printers_progress = {}
    
    # Stop all current printer sessions
    for printer in printers:
        printer.quit()
    
    # Clear all threads except Flask thread and restart_main thread
    for thread in threading.enumerate():
        if (thread is not threading.main_thread() and 
            thread is not flask_thread and 
            thread.name != "restart_main"):
            thread.join(timeout=5)  # Add a timeout to prevent indefinite blocking

    print("Restarting main function 2")
    # Reinitialize the main function
    main()



def main():
    email_send.send_email("3D Printer Monitor", "Server Started")

    global printers
    read_printers_json()
    # Example usage
    

    # Set up signal handler for keyboard interrupt
    signal.signal(signal.SIGINT, signal_handler)
    
    # Init Each Printer Status
    global printer_status
    printer_status = {}

    # Monitor printers using threading
    threads = []

        

    printers = []
    for printer_config in printers_json:
        print(printers_json[printer_config])
        print(f"Creating printer: {printer_config}")
        printer = create_printer(
            printers_json[printer_config]['ip'],
            printers_json[printer_config]['access_code'],
            printers_json[printer_config]['serial_number'],
            printer_config
        )
        thread = threading.Thread(target=monitor_printer, args=(printer,))
        thread.daemon = True  # Set threads as daemon so they exit when main thread exits
        thread.start()
        threads.append(thread)
    
    

    # Start Flask app in a separate thread
    global flask_thread
    if 'flask_thread' not in globals() or not flask_thread.is_alive():
        flask_thread = threading.Thread(target=start_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
    threads.append(flask_thread)

    try:
        # Wait for all threads to complete
        while any(thread.is_alive() for thread in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received in main thread. Waiting for threads to finish...")
        # The signal_handler will handle closing the sessions
    # monitor_printer(printer_b06)

if __name__ == "__main__":
    main()