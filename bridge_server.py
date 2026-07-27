#!/usr/bin/env python3
"""
Mars Rover Laptop-to-Phone WiFi Bridge Server
---------------------------------------------
Bridges your Android phone's web browser directly to the HC-05 Bluetooth module!
No hardware changes needed! No special apps needed!

Usage:
  python bridge_server.py [COM_PORT] [BAUD]
"""

import sys
import os
import time
import json
import socket
import threading
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("WARNING: 'pyserial' package missing! Install via: pip install pyserial")

# Global State
ser_conn = None
is_connected = False
serial_queue = queue.Queue()
latest_telemetry = {
    "temperature": "--",
    "humidity": "--",
    "mq135": "--",
    "air_rating": "UNKNOWN",
    "turbidity": "--",
    "tds": "--",
    "state": "STOPPED",
    "last_cmd": "S",
    "connected": False
}

def get_local_ip():
    """Find local WiFi network IP address of laptop"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def serial_reader_thread():
    """Continuously read HC-05 telemetry packets"""
    global is_connected, latest_telemetry
    while is_connected and ser_conn and ser_conn.is_open:
        try:
            line = ser_conn.readline().decode('utf-8', errors='ignore').strip()
            if line:
                parse_telemetry_line(line)
        except Exception:
            break
    is_connected = False
    latest_telemetry["connected"] = False

def parse_telemetry_line(line):
    global latest_telemetry
    if "Temperature" in line and ":" in line:
        latest_telemetry["temperature"] = line.split(":")[1].strip()
    elif "Humidity" in line and ":" in line:
        latest_telemetry["humidity"] = line.split(":")[1].strip()
    elif "MQ135" in line and ":" in line:
        val_str = line.split(":")[1].strip()
        latest_telemetry["mq135"] = val_str
        try:
            mq_val = int(val_str.split()[0])
            if mq_val < 300:
                latest_telemetry["air_rating"] = "GOOD"
            elif mq_val < 600:
                latest_telemetry["air_rating"] = "MODERATE"
            else:
                latest_telemetry["air_rating"] = "POOR"
        except Exception:
            pass
    elif "Turbidity" in line and ":" in line:
        latest_telemetry["turbidity"] = line.split(":")[1].strip()
    elif "TDS" in line and ":" in line:
        latest_telemetry["tds"] = line.split(":")[1].strip()
    elif "Command" in line and ":" in line:
        cmd = line.split(":")[1].strip()
        latest_telemetry["last_cmd"] = cmd
        state_map = {'F': 'FORWARD', 'B': 'REVERSE', 'L': 'TURN LEFT', 'R': 'TURN RIGHT', 'S': 'STOPPED'}
        latest_telemetry["state"] = state_map.get(cmd, cmd)

def send_bluetooth_cmd(cmd_char):
    global latest_telemetry
    state_map = {'F': 'FORWARD', 'B': 'REVERSE', 'L': 'TURN LEFT', 'R': 'TURN RIGHT', 'S': 'STOPPED'}
    latest_telemetry["last_cmd"] = cmd_char
    latest_telemetry["state"] = state_map.get(cmd_char, cmd_char)

    if is_connected and ser_conn and ser_conn.is_open:
        try:
            ser_conn.write(cmd_char.encode('utf-8'))
            print(f"[TX] Command -> {cmd_char}")
            return True
        except Exception as e:
            print(f"[TX ERR] {e}")
            return False
    else:
        print(f"[SIMULATION TX] Command -> {cmd_char}")
        return True

class RoverBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # CORS Headers for phone browser access
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        if path == '/api/cmd':
            cmd = params.get('c', ['S'])[0]
            success = send_bluetooth_cmd(cmd)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "cmd": cmd, "tx": success}).encode('utf-8'))

        elif path == '/api/telemetry':
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(latest_telemetry).encode('utf-8'))

        elif path == '/api/status':
            ports = [p.device for p in serial.tools.list_ports.comports()] if SERIAL_AVAILABLE else []
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "connected": is_connected,
                "available_ports": ports
            }).encode('utf-8'))

        else:
            # Serve index.html or static files
            file_path = "index.html" if path == "/" else path.lstrip("/")
            if os.path.exists(file_path) and os.path.isfile(file_path):
                content_type = "text/html"
                if file_path.endswith(".js"): content_type = "application/javascript"
                elif file_path.endswith(".json"): content_type = "application/json"
                elif file_path.endswith(".css"): content_type = "text/css"

                self.send_header('Content-Type', content_type)
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"404 Not Found")

def connect_serial_port(port, baud=9600):
    global ser_conn, is_connected, latest_telemetry
    if not SERIAL_AVAILABLE:
        print("pyserial module not available.")
        return False
    try:
        ser_conn = serial.Serial(port, baud, timeout=1)
        is_connected = True
        latest_telemetry["connected"] = True
        print(f"[OK] Bluetooth connected on {port} at {baud} baud.")
        rx_thread = threading.Thread(target=serial_reader_thread, daemon=True)
        rx_thread.start()
        return True
    except Exception as e:
        print(f"[ERR] Could not open {port}: {e}")
        return False

def auto_connect_bluetooth():
    if not SERIAL_AVAILABLE:
        return
    ports = [p.device for p in serial.tools.list_ports.comports()]
    print(f"Scanning COM ports: {ports}")
    for port in ports:
        if "COM" in port.upper():
            print(f"Attempting connection to {port}...")
            if connect_serial_port(port):
                break

def start_server(port=8080):
    local_ip = get_local_ip()
    server = HTTPServer(('0.0.0.0', port), RoverBridgeHandler)
    
    print("\n" + "="*60)
    print(" MARS ROVER MOBILE PHONE BRIDGE SERVER ACTIVE")
    print("="*60)
    print(f" OPEN THIS LINK ON YOUR PHONE CHROME BROWSER:")
    print(f" ->   http://{local_ip}:{port}")
    print("="*60 + "\n")

    auto_connect_bluetooth()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down bridge server...")
        if ser_conn and ser_conn.is_open:
            ser_conn.close()

if __name__ == "__main__":
    port_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if port_arg:
        connect_serial_port(port_arg)
    start_server(8080)
