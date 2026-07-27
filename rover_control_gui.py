#!/usr/bin/env python3
"""
Mars Rover Mission Control Dashboard
-------------------------------------
Desktop GUI to wirelessly control the Mars Rover over Bluetooth/Serial,
display live telemetry (Temperature, Humidity, Air Quality, Water Quality),
and drive the rover using on-screen buttons or Keyboard WASD / Arrow keys.
"""

import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Serial Communication
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class MarsRoverControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔴 MARS ROVER MISSION CONTROL DASHBOARD")
        self.root.geometry("980x700")
        self.root.minsize(850, 600)
        self.root.configure(bg="#0B0E14")

        # Serial Connection State
        self.ser = None
        self.is_connected = False
        self.telemetry_queue = queue.Queue()
        self.rx_thread = None

        # Key state tracking and release debounce timer dict
        self.pressed_keys = set()
        self.release_timers = {}

        # Telemetry Data Variables
        self.temp_var = tk.StringVar(value="-- °C")
        self.hum_var = tk.StringVar(value="-- %")
        self.mq135_var = tk.StringVar(value="--")
        self.air_status_var = tk.StringVar(value="UNKNOWN")
        self.turb_var = tk.StringVar(value="--")
        self.tds_var = tk.StringVar(value="--")
        self.state_var = tk.StringVar(value="DISCONNECTED")
        self.cmd_var = tk.StringVar(value="S")
        self.conn_status_var = tk.StringVar(value="Disconnected")

        # Custom Dark Theme Styles
        self.setup_styles()

        # Build UI Sections
        self.create_header()
        self.create_main_layout()

        # Start periodic GUI updates
        self.root.after(100, self.process_telemetry_queue)
        self.root.after(1000, self.refresh_com_ports)

        # Bind Keyboard Events
        self.bind_keyboard_controls()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configure custom TTK colors
        self.style.configure(".", background="#0B0E14", foreground="#FFFFFF")
        self.style.configure("TFrame", background="#0B0E14")
        self.style.configure("Card.TFrame", background="#1A1F2C", relief="flat")
        self.style.configure("TLabel", background="#1A1F2C", foreground="#E0E6ED", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background="#0B0E14", foreground="#00E5FF", font=("Segoe UI", 16, "bold"))
        self.style.configure("CardTitle.TLabel", background="#1A1F2C", foreground="#94A3B8", font=("Segoe UI", 9, "bold"))
        self.style.configure("CardVal.TLabel", background="#1A1F2C", foreground="#FFFFFF", font=("Segoe UI", 20, "bold"))
        self.style.configure("Status.TLabel", background="#1A1F2C", foreground="#00E676", font=("Segoe UI", 14, "bold"))

        # Combobox style
        self.style.configure("TCombobox", fieldbackground="#242B3D", background="#242B3D", foreground="#FFFFFF", borderwidth=0)
        self.style.map("TCombobox", fieldbackground=[("readonly", "#242B3D")], foreground=[("readonly", "#FFFFFF")])

    def create_header(self):
        header_frame = ttk.Frame(self.root, style="TFrame", padding=(15, 10, 15, 5))
        header_frame.pack(fill=tk.X)

        title_lbl = ttk.Label(header_frame, text="🔴 MARS ROVER TELEMETRY & COMMAND CENTER", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT)

        # Connection Controls
        conn_frame = ttk.Frame(header_frame, style="TFrame")
        conn_frame.pack(side=tk.RIGHT)

        ttk.Label(conn_frame, text="Port: ", background="#0B0E14", foreground="#94A3B8").pack(side=tk.LEFT, padx=2)

        self.port_combobox = ttk.Combobox(conn_frame, width=12, state="readonly")
        self.port_combobox.pack(side=tk.LEFT, padx=4)

        refresh_btn = tk.Button(conn_frame, text="🔄", command=self.refresh_com_ports, bg="#242B3D", fg="#FFFFFF",
                                activebackground="#333D56", activeforeground="#FFFFFF", bd=0, padx=6, pady=2, font=("Segoe UI", 9))
        refresh_btn.pack(side=tk.LEFT, padx=2)

        ttk.Label(conn_frame, text=" Baud: ", background="#0B0E14", foreground="#94A3B8").pack(side=tk.LEFT, padx=2)
        self.baud_combobox = ttk.Combobox(conn_frame, values=["9600", "115200"], width=7, state="readonly")
        self.baud_combobox.set("9600")
        self.baud_combobox.pack(side=tk.LEFT, padx=4)

        self.connect_btn = tk.Button(conn_frame, text="CONNECT", command=self.toggle_connection,
                                     bg="#00E676", fg="#000000", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=4, cursor="hand2")
        self.connect_btn.pack(side=tk.LEFT, padx=8)

    def create_main_layout(self):
        # Container
        main_container = ttk.Frame(self.root, style="TFrame", padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left Column: Telemetry Dashboard Cards
        telemetry_frame = ttk.Frame(main_container, style="TFrame")
        telemetry_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Grid of Cards
        telemetry_frame.columnconfigure(0, weight=1)
        telemetry_frame.columnconfigure(1, weight=1)

        # 1. Temperature Card
        card_temp = self.create_card(telemetry_frame, "🌡️ TEMPERATURE", self.temp_var, "#FF5252", 0, 0)
        
        # 2. Humidity Card
        card_hum = self.create_card(telemetry_frame, "💧 HUMIDITY", self.hum_var, "#00E5FF", 0, 1)

        # 3. MQ135 Air Quality Card
        card_mq = self.create_card_with_subtext(telemetry_frame, "💨 AIR QUALITY (MQ135)", self.mq135_var, self.air_status_var, "#FFC400", 1, 0)

        # 4. Turbidity Card
        card_turb = self.create_card(telemetry_frame, "🌊 TURBIDITY (RAW)", self.turb_var, "#651FFF", 1, 1)

        # 5. TDS Card
        card_tds = self.create_card(telemetry_frame, "🧪 WATER TDS (RAW)", self.tds_var, "#00E676", 2, 0)

        # 6. Rover Motion Status Card
        card_status = self.create_card_with_subtext(telemetry_frame, "🛸 ROVER STATE", self.state_var, self.cmd_var, "#FF9100", 2, 1)

        # Right Column: Directional Drive Controls
        control_frame = ttk.Frame(main_container, style="TFrame", padding=10)
        control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

        ctrl_card = ttk.Frame(control_frame, style="Card.TFrame", padding=20)
        ctrl_card.pack(fill=tk.BOTH, expand=True)

        ctrl_title = ttk.Label(ctrl_card, text="🎮 MOBILITY DRIVE CONTROL", style="CardTitle.TLabel")
        ctrl_title.pack(anchor=tk.CENTER, pady=(0, 15))

        # D-Pad Button Grid
        dpad_frame = tk.Frame(ctrl_card, bg="#1A1F2C")
        dpad_frame.pack(pady=10)

        btn_style = {"font": ("Segoe UI", 12, "bold"), "width": 8, "height": 2, "bd": 0, "cursor": "hand2"}

        self.btn_up = tk.Button(dpad_frame, text="▲\nFORWARD\n(W / ↑)",
                                bg="#242B3D", fg="#00E5FF", activebackground="#00E5FF", activeforeground="#000000", **btn_style)
        self.btn_up.grid(row=0, column=1, padx=5, pady=5)
        self.btn_up.bind("<ButtonPress-1>", lambda e: self.on_btn_press('F', self.btn_up))
        self.btn_up.bind("<ButtonRelease-1>", lambda e: self.on_btn_release(self.btn_up))

        self.btn_left = tk.Button(dpad_frame, text="◄ LEFT\n(A / ←)",
                                  bg="#242B3D", fg="#00E5FF", activebackground="#00E5FF", activeforeground="#000000", **btn_style)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.btn_left.bind("<ButtonPress-1>", lambda e: self.on_btn_press('L', self.btn_left))
        self.btn_left.bind("<ButtonRelease-1>", lambda e: self.on_btn_release(self.btn_left))

        self.btn_stop = tk.Button(dpad_frame, text="█ STOP\n(SPACE)", command=lambda: self.send_command('S'),
                                  bg="#FF1744", fg="#FFFFFF", activebackground="#D50000", activeforeground="#FFFFFF", **btn_style)
        self.btn_stop.grid(row=1, column=1, padx=5, pady=5)

        self.btn_right = tk.Button(dpad_frame, text="RIGHT ►\n(D / →)",
                                   bg="#242B3D", fg="#00E5FF", activebackground="#00E5FF", activeforeground="#000000", **btn_style)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)
        self.btn_right.bind("<ButtonPress-1>", lambda e: self.on_btn_press('R', self.btn_right))
        self.btn_right.bind("<ButtonRelease-1>", lambda e: self.on_btn_release(self.btn_right))

        self.btn_down = tk.Button(dpad_frame, text="▼\nREVERSE\n(S / ↓)",
                                  bg="#242B3D", fg="#00E5FF", activebackground="#00E5FF", activeforeground="#000000", **btn_style)
        self.btn_down.grid(row=2, column=1, padx=5, pady=5)
        self.btn_down.bind("<ButtonPress-1>", lambda e: self.on_btn_press('B', self.btn_down))
        self.btn_down.bind("<ButtonRelease-1>", lambda e: self.on_btn_release(self.btn_down))

        # Instructions Label
        info_lbl = tk.Label(ctrl_card, text="💡 Tip: Hold buttons or Keyboard WASD / Arrow Keys to drive. Release to stop.",
                            bg="#1A1F2C", fg="#94A3B8", font=("Segoe UI", 9), wraplength=220, justify=tk.CENTER)
        info_lbl.pack(pady=(15, 0))

        # Bottom Console Log Frame
        console_frame = ttk.Frame(self.root, style="TFrame", padding=(15, 0, 15, 15))
        console_frame.pack(fill=tk.BOTH, expand=True)

        console_card = ttk.Frame(console_frame, style="Card.TFrame", padding=10)
        console_card.pack(fill=tk.BOTH, expand=True)

        c_title = ttk.Label(console_card, text="📜 LIVE DATA PACKET CONSOLE", style="CardTitle.TLabel")
        c_title.pack(anchor=tk.W, pady=(0, 5))

        self.console_text = tk.Text(console_card, height=6, bg="#0B0E14", fg="#00E676",
                                    insertbackground="#FFFFFF", font=("Consolas", 9), bd=0, relief=tk.FLAT)
        self.console_text.pack(fill=tk.BOTH, expand=True)

    def create_card(self, parent, title, val_var, color, row, col):
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

        lbl_title = ttk.Label(card, text=title, style="CardTitle.TLabel")
        lbl_title.pack(anchor=tk.W)

        lbl_val = ttk.Label(card, textvariable=val_var, style="CardVal.TLabel", foreground=color)
        lbl_val.pack(anchor=tk.W, pady=(8, 0))
        return card

    def create_card_with_subtext(self, parent, title, val_var, sub_var, color, row, col):
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

        lbl_title = ttk.Label(card, text=title, style="CardTitle.TLabel")
        lbl_title.pack(anchor=tk.W)

        val_frame = tk.Frame(card, bg="#1A1F2C")
        val_frame.pack(fill=tk.X, pady=(5, 0))

        lbl_val = ttk.Label(val_frame, textvariable=val_var, style="CardVal.TLabel", foreground=color)
        lbl_val.pack(side=tk.LEFT)

        lbl_sub = tk.Label(val_frame, textvariable=sub_var, bg="#242B3D", fg="#00E5FF",
                          font=("Segoe UI", 9, "bold"), padx=8, pady=2)
        lbl_sub.pack(side=tk.RIGHT, padx=5)
        return card

    def bind_keyboard_controls(self):
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)

    def on_key_press(self, event):
        key = event.keysym.lower()

        # If there's a pending release timer for this key (from Windows OS auto-repeat), cancel it!
        if key in self.release_timers:
            self.root.after_cancel(self.release_timers[key])
            del self.release_timers[key]

        if key in self.pressed_keys:
            return  # Already active, ignore repeat

        self.pressed_keys.add(key)

        if key in ['w', 'up']:
            self.send_command('F')
            self.highlight_btn(self.btn_up, True)
        elif key in ['s', 'down']:
            self.send_command('B')
            self.highlight_btn(self.btn_down, True)
        elif key in ['a', 'left']:
            self.send_command('L')
            self.highlight_btn(self.btn_left, True)
        elif key in ['d', 'right']:
            self.send_command('R')
            self.highlight_btn(self.btn_right, True)
        elif key in ['space']:
            self.send_command('S')
            self.highlight_btn(self.btn_stop, True)

    def on_btn_press(self, cmd, btn):
        self.send_command(cmd)
        self.highlight_btn(btn, True)

    def on_btn_release(self, btn):
        self.send_command('S')
        self.highlight_btn(btn, False)

    def on_key_release(self, event):
        key = event.keysym.lower()

        # Schedule release confirmation after 60ms to filter Windows OS key auto-repeat
        if key in self.release_timers:
            self.root.after_cancel(self.release_timers[key])

        timer_id = self.root.after(60, lambda k=key: self.confirm_key_release(k))
        self.release_timers[key] = timer_id

    def confirm_key_release(self, key):
        if key in self.release_timers:
            del self.release_timers[key]

        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

        movement_keys = {'w', 'up', 's', 'down', 'a', 'left', 'd', 'right'}
        if key in movement_keys:
            # If no other movement keys are currently held, send STOP command
            if not any(k in self.pressed_keys for k in movement_keys):
                self.send_command('S')

            if key in ['w', 'up']:
                self.highlight_btn(self.btn_up, False)
            elif key in ['s', 'down']:
                self.highlight_btn(self.btn_down, False)
            elif key in ['a', 'left']:
                self.highlight_btn(self.btn_left, False)
            elif key in ['d', 'right']:
                self.highlight_btn(self.btn_right, False)
        elif key in ['space']:
            self.highlight_btn(self.btn_stop, False)

    def highlight_btn(self, btn, active):
        if active:
            btn.config(bg="#00E5FF", fg="#000000")
        else:
            if btn == self.btn_stop:
                btn.config(bg="#FF1744", fg="#FFFFFF")
            else:
                btn.config(bg="#242B3D", fg="#00E5FF")

    def refresh_com_ports(self):
        if not SERIAL_AVAILABLE:
            self.port_combobox['values'] = ["pyserial missing"]
            return

        ports = [port.device for port in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["No Ports Found"]
        
        current = self.port_combobox.get()
        self.port_combobox['values'] = ports
        if current not in ports:
            self.port_combobox.set(ports[0])

    def toggle_connection(self):
        if not SERIAL_AVAILABLE:
            messagebox.showerror("Error", "pyserial module is not installed!\nRun: pip install pyserial")
            return

        if self.is_connected:
            self.disconnect_serial()
        else:
            port = self.port_combobox.get()
            baud = int(self.baud_combobox.get())
            if not port or port == "No Ports Found":
                messagebox.showwarning("Connection Error", "Please select a valid Bluetooth / Serial COM port.")
                return
            self.connect_serial(port, baud)

    def connect_serial(self, port, baud):
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.is_connected = True
            self.state_var.set("CONNECTED / IDLE")
            self.connect_btn.config(text="DISCONNECT", bg="#FF1744", fg="#FFFFFF")
            self.log_console(f"Connected to {port} at {baud} baud.\n")

            # Start RX Thread
            self.rx_thread = threading.Thread(target=self.serial_reader_thread, daemon=True)
            self.rx_thread.start()

        except Exception as e:
            messagebox.showerror("Connection Failed", f"Could not open port {port}:\n{e}")

    def disconnect_serial(self):
        self.is_connected = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.connect_btn.config(text="CONNECT", bg="#00E676", fg="#000000")
        self.state_var.set("DISCONNECTED")
        self.log_console("Disconnected from Bluetooth / Serial port.\n")

    def send_command(self, cmd_char):
        self.cmd_var.set(cmd_char)
        if self.is_connected and self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd_char.encode('utf-8'))
                self.log_console(f"TX -> Command: '{cmd_char}'\n")
            except Exception as e:
                self.log_console(f"TX Error: {e}\n")
        else:
            self.log_console(f"Offline Simulation TX -> Command: '{cmd_char}'\n")

    def serial_reader_thread(self):
        while self.is_connected and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self.telemetry_queue.put(line)
            except Exception:
                break
        self.is_connected = False

    def process_telemetry_queue(self):
        while not self.telemetry_queue.empty():
            line = self.telemetry_queue.get()
            self.log_console(f"RX <- {line}\n")
            self.parse_telemetry(line)

        self.root.after(100, self.process_telemetry_queue)

    def parse_telemetry(self, line):
        # 1. Flexible parsing for standard Arduino Serial output lines
        if "Temperature" in line and ":" in line:
            val = line.split(":")[1].strip()
            self.temp_var.set(val)
        elif "Humidity" in line and ":" in line:
            val = line.split(":")[1].strip()
            self.hum_var.set(val)
        elif "MQ135" in line and ":" in line:
            val = line.split(":")[1].strip()
            self.mq135_var.set(val)
            try:
                mq_val = int(val.split()[0])
                if mq_val < 300:
                    self.air_status_var.set("GOOD")
                elif mq_val < 600:
                    self.air_status_var.set("MODERATE")
                else:
                    self.air_status_var.set("POOR")
            except Exception:
                pass
        elif "Turbidity" in line and ":" in line:
            val = line.split(":")[1].strip()
            self.turb_var.set(val)
        elif "TDS" in line and ":" in line:
            val = line.split(":")[1].strip()
            self.tds_var.set(val)
        elif "Command" in line and ":" in line:
            cmd = line.split(":")[1].strip()
            self.cmd_var.set(cmd)
            state_map = {'F': 'FORWARD', 'B': 'BACKWARD', 'L': 'TURN LEFT', 'R': 'TURN RIGHT', 'S': 'STOPPED'}
            self.state_var.set(state_map.get(cmd, cmd))

        # 2. Backward compatible DATA: payload format
        elif line.startswith("DATA:"):
            payload = line[5:].split(',')
            if len(payload) >= 6:
                temp_str, hum_str, mq_str, turb_str, tds_str, state_str = payload[:6]

                self.temp_var.set(f"{temp_str} °C")
                self.hum_var.set(f"{hum_str} %")
                self.mq135_var.set(mq_str)
                self.turb_var.set(turb_str)
                self.tds_var.set(tds_str)
                self.state_var.set(state_str.upper())

                try:
                    mq_val = int(mq_str)
                    if mq_val < 300:
                        self.air_status_var.set("GOOD")
                    elif mq_val < 600:
                        self.air_status_var.set("MODERATE")
                    else:
                        self.air_status_var.set("POOR")
                except ValueError:
                    self.air_status_var.set("OK")

    def log_console(self, text):
        self.console_text.insert(tk.END, text)
        self.console_text.see(tk.END)


if __name__ == "__main__":
    if not SERIAL_AVAILABLE:
        print("Warning: 'pyserial' library not found. Install via 'pip install pyserial'")

    root = tk.Tk()
    app = MarsRoverControlApp(root)
    root.mainloop()
