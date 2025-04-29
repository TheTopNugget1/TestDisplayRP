import serial
import time
import tkinter as tk
from tkinter import HORIZONTAL, ttk

class ServoController:
    def __init__(self, arduino, servo_id):
        self.arduino = arduino
        self.servo_id = servo_id  # ID for the servo
        self.pot_control = True  # Default mode: potentiometer control
        self.error_label = None  # Will hold the error label

    def send_servo_angle(self, angle): # sends the comand to the arduino
        command = f"{self.servo_id}:{angle}\n"  # formats the command
        try:
            self.arduino.write(command.encode())  # send command to Arduino
            print(command)
        except serial.SerialException:
            print("Error: Arduino disconnected.")

    def toggle_mode(self): # Switches between potentiometer control and user input.
        self.pot_control = not self.pot_control
        try:
            self.arduino.reset_input_buffer()
            mode_command = f"{self.servo_id}:{'True' if self.pot_control else 'False'}\n"
            self.arduino.write(mode_command.encode())
            print(mode_command)
        except serial.SerialException:
            print("Error: Arduino disconnected.")
        return self.pot_control

    def send_questionmark(self, val): #Validates and sends typed user input to the servo.
        if self.arduino != None:
            try:
                data = int(float(val))  # safely convert input to int
                if not self.pot_control:
                    if 0 <= data <= 160:
                        self.send_servo_angle(data)
                        self.error_label.config(text="")  # clear error if valid
                    else:
                        print("INVALID: Out of range (0-160)")
                        self.error_label.config(text=f"INVALID: {val} is not in range (0-160)")
                else:
                    print("INVALID: Incorrect input mode")
                    self.error_label.config(text="INVALID: Incorrect input mode")
            except ValueError:
                print("INVALID: Not a number")
                self.error_label.config(text=f"INVALID: {val} is not a number")
        else: 
            print("Input Error: Arduino disconnected")
            return

class ServoGUI:
    def __init__(self, root, servo_controllers, arduino):
        # Store references to the main window, servo controllers, and Arduino serial connection
        self.root = root
        self.servos = servo_controllers
        self.arduino = arduino  # serial connection object
        self.pot_values = {}  # Store latest potentiometer readings
        self.connected = False  # Track connection status for status display

        # Build the GUI and debug panel
        self.setup_gui()
        self.show_debug_panel()
        # Start displaying connection status
        self.update_connection_status()

    def try_connect(self): # Attempts to connect to Arduino or detects disconnection, called repeatedly
        
        global arduino
        if arduino is None:
            # Try establishing a new serial connection
            try:
                if not hasattr(self, 'loading_popup'):
                    self.show_loading("Connecting to Arduino...")  # Show loading while trying

                arduino = serial.Serial('COM7', 115200, timeout=1)

                self.root.after(1000, self.finish_reconnect)

            except serial.SerialException:
                pass  # Ignore and retry next cycle
        else:
            # Check if existing serial connection is still valid
            try:
                test = arduino.in_waiting  # Test read property to detect errors
            except serial.SerialException:
                print("Connection lost. Closing serial.")
                try:
                    arduino.close()  # Attempt to close the faulty serial handle
                except Exception:
                    pass

                # Clear serial connection references
                arduino = None
                self.arduino = None
                for servo in self.servos.values():
                    servo.arduino = None

                self.show_loading("Reconnecting to Arduino...")  # Show spinner if lost

        # Update GUI connection status display
        self.update_connection_status()
        # Schedule to check connection again in 1 second
        self.root.after(1000, self.try_connect)

    def finish_reconnect(self):
        """Finishes setting up Arduino after waiting."""
        global arduino
        if arduino:
            self.arduino = arduino
            for servo in self.servos.values():
                servo.arduino = arduino
            print("Arduino reconnected")
            self.hide_loading()

    def setup_gui(self): # Creates the main servo control GUI layout
        
        self.root.geometry("500x400")
        self.root.title("Multi-Servo Controller")
        self.root.configure(bg="#f0f0f0")

        # Create a frame to hold widgets
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True, fill="both")

        # Title label
        ttk.Label(frame, text="Servo Control Panel", font=("Arial", 14, "bold"), background="#f0f0f0").grid(column=0, row=0, columnspan=2, pady=10)

        # Dictionaries to track sliders and mode labels
        self.sliders = {}
        self.mode_labels = {}

        # Create controls for each servo
        for idx, (servo_name, servo) in enumerate(self.servos.items()):
            # Mode label (Potentiometer/User)
            self.mode_labels[servo_name] = ttk.Label(frame, text=f"{servo_name} Mode: Potentiometer", font=("Arial", 10), background="#f0f0f0")
            self.mode_labels[servo_name].grid(column=0, row=idx * 2 + 1, columnspan=2, pady=5)

            # Slider for live value control
            self.sliders[servo_name] = tk.IntVar()
            slider = ttk.Scale(frame, variable=self.sliders[servo_name], from_=0, to=160, orient=HORIZONTAL,
                               command=lambda val, s=servo: s.send_questionmark(val))
            slider.grid(column=0, row=idx * 2 + 2, pady=10, padx=20, sticky="ew")

            # Mode toggle button
            toggle_btn = ttk.Button(frame, text=f"Toggle {servo_name} Mode", command=lambda s=servo, n=servo_name: self.toggle_mode(s, n))
            toggle_btn.grid(column=1, row=idx * 2 + 2, pady=5)

            # Text entry for typing a value
            angle_var = tk.StringVar()
            entry = ttk.Entry(frame, textvariable=angle_var, width=5)
            entry.grid(column=2, row=idx * 2 + 2, padx=5)
            entry.bind("<Return>", lambda event, s=servo, v=angle_var: (s.send_questionmark(v.get()), v.set("")))

            # Error message label beside the entry field
            error_label = tk.Label(frame, text="", fg="red")
            error_label.grid(row=idx * 2 + 2, column=3, padx=5)
            servo.error_label = error_label  # Attach error label to controller

        # Quit button to close the app
        ttk.Button(frame, text="Quit", command=self.root.destroy).grid(column=0, row=len(self.servos) * 2 + 2, columnspan=2, pady=10)

        # Connection status label
        self.status_label = ttk.Label(frame, text="Arduino Status: Unknown", background="#f0f0f0")
        self.status_label.grid(column=0, row=len(self.servos)*2+3, columnspan=3, pady=5)

    def toggle_mode(self, servo, servo_name):
        if self.arduino != None:
            new_mode = servo.toggle_mode()
            mode_text = "Potentiometer" if new_mode else "User Input"
            self.mode_labels[servo_name].config(text=f"{servo_name} Mode: {mode_text}")
        else:
            print("Input Error: Arduino disconnected")
            return

    def read_sensor(self):
        try:
            if self.arduino and self.arduino.in_waiting > 0:
                data = self.arduino.readline().decode().strip()
                if data.isdigit():
                    return int(data)
        except serial.SerialException:
            print("Read Error: Arduino disconnected.")
        return None

    def update_buffer(self):
        try:
            if not self.arduino or not self.arduino.is_open:
                raise serial.SerialException
            test = self.arduino.in_waiting  # Just checking if Arduino is alive
        except serial.SerialException:
            self.root.after(100, self.update_buffer)
            return

        try:
            # Update debug panel buffer lengths
            self.in_buffer_len.set(f"Input Buffer: {self.arduino.in_waiting}")
            self.out_buffer_len.set(f"Output Buffer: {self.arduino.out_waiting}")

            # Process all available data immediately
            while self.arduino.in_waiting > 0:
                try:
                    raw_data = self.arduino.readline().decode().strip()
                    if raw_data:  # Only process non-empty lines
                        self.process_pot_data(raw_data)
                except serial.SerialException:
                    print("Buffer Error while reading.")
                    break  # Arduino got disconnected while reading

        except serial.SerialException:
            print("Buffer Error: Arduino disconnected.")

        self.root.after(100, self.update_buffer)
        
    def process_pot_data(self, data):
        try:
            parts = data.split(":")
            if len(parts) == 2:
                pin = parts[0]
                value = int(parts[1])
                self.pot_values[pin] = value
                if pin in self.pot_labels:
                    self.pot_labels[pin].set(f"{value}")
                if pin in self.pot_bars:
                    self.pot_bars[pin]['value'] = value
        except ValueError:
            pass

    def show_debug_panel(self):
        debug_window = tk.Toplevel()
        debug_window.title("Debug Window")
        debug_window.geometry("200x250")
        debug_window.configure(bg="#e6e6e6")

        frame = tk.Frame(debug_window, padx=20, pady=20, bg="#e6e6e6")
        frame.pack(expand=True, fill="both")

        ttk.Label(frame, text="Debug Information", font=("Arial", 12, "bold"), background="#e6e6e6").grid(column=0, row=0, pady=10)

        self.in_buffer_len = tk.StringVar(value="Input Buffer Length: 0")
        ttk.Label(frame, textvariable=self.in_buffer_len, background="#e6e6e6").grid(column=0, row=1, pady=5)

        self.out_buffer_len = tk.StringVar(value="Output Buffer Length: 0")
        ttk.Label(frame, textvariable=self.out_buffer_len, background="#e6e6e6").grid(column=0, row=2, pady=5)

        # Section title
        ttk.Label(frame, text="Potentiometer Readings", font=("Arial", 12, "underline"), background="#e6e6e6").grid(column=0, row=5, columnspan=2, pady=(20, 5))

        # Potentiometer values and bars
        self.pot_labels = {}
        self.pot_bars = {}

        for idx, pin in enumerate(["A0", "A1", "A2"]):
            ttk.Label(frame, text=f"{pin}:", background="#e6e6e6").grid(column=0, row=6 + idx*2, sticky="w")
            self.pot_labels[pin] = tk.StringVar(value="0")
            self.pot_bars[pin] = ttk.Progressbar(frame, maximum=1023, length=200)
            self.pot_bars[pin].grid(column=0, row=7 + idx*2, columnspan=2, pady=2)
            ttk.Label(frame, textvariable=self.pot_labels[pin], background="#e6e6e6").grid(column=1, row=6 + idx*2, sticky="e")

        self.update_buffer()

    def update_connection_status(self):
        try:
            if self.arduino and self.arduino.is_open:
                self.status_label.config(text="Arduino Status: Connected")
            else:
                self.status_label.config(text="Arduino Status: Disconnected")
                print("Waiting for connection...")
        except serial.SerialException:
            self.status_label.config(text="Arduino Status: Disconnected")
            print("Waiting for connection...")

    def show_loading(self, message="Working..."):
        """Shows a loading popup with an animated spinner."""
        if hasattr(self, 'loading_popup'):
            return  # Already showing

        self.loading_popup = tk.Toplevel(self.root)
        self.loading_popup.title("Please wait")
        self.loading_popup.geometry("250x120")
        self.loading_popup.configure(bg="#f0f0f0")
        self.loading_popup.resizable(False, False)

        tk.Label(self.loading_popup, text=message, font=("Arial", 12), bg="#f0f0f0").pack(pady=10)

        self.loading_bar = ttk.Progressbar(self.loading_popup, mode="indeterminate")
        self.loading_bar.pack(pady=10, padx=20, fill="x")
        self.loading_bar.start(10)  # Speed of bouncing

        self.loading_popup.update_idletasks()

    def hide_loading(self):
        """Closes the loading popup if it is open."""
        if hasattr(self, 'loading_popup'):
            self.loading_bar.stop()
            self.loading_popup.destroy()
            del self.loading_popup

if __name__ == "__main__":
    arduino = None
    servo_controllers = {
        "Servo 1": ServoController(arduino, 1),
        "Servo 2": ServoController(arduino, 2),
        "Servo 3": ServoController(arduino, 3)
    }
    root = tk.Tk()
    app = ServoGUI(root, servo_controllers, arduino)
    app.try_connect()
    root.mainloop()
