from bpm.bambuconfig import BambuConfig
from bpm.bambuprinter import BambuPrinter
from redis_handler import RedisHandler
import time
import threading
import email_send

redis_handler = RedisHandler()

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

    old_state = "idle" if is_printer_idle(printer) else "printing"
    while True:

        #print(f"{printer.name} - Old Stage: {get_stage_info(printer._current_stage)}")
        current_state = "idle" if is_printer_idle(printer) else "printing"

        # This is updating the global progress variable that can be accessed by the Flask app
        progress = {
            "stage": get_stage_info(printer._current_stage),
            "progress": str(printer.percent_complete) + "%",
            "time_remaining": format_time(printer.time_remaining),
            "current_state": current_state,
            "doc": printer.jsonSerializer()
        }
        
        redis_handler.set_printer_progress(printer.name, progress)

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

def update_printer_status(name, status):
    redis_handler.set_printer_status(name, status)

def printerStateChange(name, old_state, new_state):
    print(f"{name} - State changed from {old_state} to {new_state}")
    if new_state == "printing":
        email_send.send_email(name, "Print Job Started")
    elif new_state == "idle":
        email_send.send_email(name, "Print Job Completed")

def start_mqtt_client():
    printers = redis_handler.get_printers()
    
    threads = []
    for printer_name, printer_config in printers.items():
        printer = create_printer(
            printer_config['ip'],
            printer_config['access_code'],
            printer_config['serial_number'],
            printer_name
        )
        thread = threading.Thread(target=monitor_printer, args=(printer,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    start_mqtt_client()