import tkinter as tk
from tkinter import messagebox
import serial
import time
import threading

class CNCControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CNC Gantry Control")
        self.root.geometry("600x600")

        # Initialize serial connection
        try:
            self.ser = serial.Serial('COM4', 9600, timeout=1)  # Adjust COM port
            time.sleep(2)  # Wait for Arduino to reset
        except serial.SerialException:
            messagebox.showerror("Error", "Failed to connect to Arduino. Check COM port.")
            self.root.quit()

        # Step size entry
        tk.Label(root, text="Step Size (for buttons):").pack(pady=5)
        self.step_size = tk.Entry(root)
        self.step_size.insert(0, "100")  # Default step size
        self.step_size.pack()

        # Speed control slider
        tk.Label(root, text="Speed (Higher = Faster):").pack(pady=5)
        self.speed_var = tk.IntVar(value=500)  # Default speed (µs delay)
        self.speed_slider = tk.Scale(root, from_=2000, to=500, orient=tk.HORIZONTAL, variable=self.speed_var)
        self.speed_slider.pack()

        # Manual position setting
        tk.Label(root, text="Set Position (0-8200 steps):").pack(pady=5)
        pos_frame = tk.Frame(root)
        tk.Label(pos_frame, text="X:").pack(side=tk.LEFT)
        self.x_pos_entry = tk.Entry(pos_frame, width=10)
        self.x_pos_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(pos_frame, text="Y:").pack(side=tk.LEFT)
        self.y_pos_entry = tk.Entry(pos_frame, width=10)
        self.y_pos_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(pos_frame, text="Set", command=self.set_position).pack(side=tk.LEFT, padx=5)
        pos_frame.pack()

        # X-axis control
        tk.Label(root, text="X-Axis (Controls X and Z)").pack(pady=5)
        x_frame = tk.Frame(root)
        tk.Button(x_frame, text="X+", command=lambda: self.move_axis('X', True)).pack(side=tk.LEFT, padx=5)
        tk.Button(x_frame, text="X-", command=lambda: self.move_axis('X', False)).pack(side=tk.LEFT, padx=5)
        x_frame.pack()

        # X-axis position slider
        tk.Label(root, text="X Position (0-8200 steps):").pack(pady=5)
        self.x_pos_var = tk.DoubleVar(value=0)
        self.x_pos_slider = tk.Scale(root, from_=0, to=8200, orient=tk.HORIZONTAL, variable=self.x_pos_var, command=self.on_x_slider_move)
        self.x_pos_slider.pack()

        # Y-axis control
        tk.Label(root, text="Y-Axis").pack(pady=5)
        y_frame = tk.Frame(root)
        tk.Button(y_frame, text="Y+", command=lambda: self.move_axis('Y', True)).pack(side=tk.LEFT, padx=5)
        tk.Button(y_frame, text="Y-", command=lambda: self.move_axis('Y', False)).pack(side=tk.LEFT, padx=5)
        y_frame.pack()

        # Y-axis position slider
        tk.Label(root, text="Y Position (0-8200 steps):").pack(pady=5)
        self.y_pos_var = tk.DoubleVar(value=0)
        self.y_pos_slider = tk.Scale(root, from_=0, to=8200, orient=tk.HORIZONTAL, variable=self.y_pos_var, command=self.on_y_slider_move)
        self.y_pos_slider.pack()

        # Home button
        tk.Button(root, text="Home (0,0)", command=self.home).pack(pady=10)

        # Stop button
        tk.Button(root, text="STOP", command=self.stop, bg="red", fg="white").pack(pady=10)

        # Position display
        tk.Label(root, text="Current Position (steps):").pack(pady=5)
        self.pos_label = tk.Label(root, text="X: 0, Y: 0")
        self.pos_label.pack()

        # Status label
        self.status = tk.Label(root, text="Ready")
        self.status.pack(pady=10)

        # Start position update thread
        self.running = True
        self.update_thread = threading.Thread(target=self.update_position)
        self.update_thread.daemon = True
        self.update_thread.start()

        # Flag to prevent slider command spam
        self.slider_moving = False

    def move_axis(self, axis, direction):
        try:
            steps = int(self.step_size.get())
            if steps <= 0:
                raise ValueError("Step size must be positive")
            speed = self.speed_var.get()
            command = f"{axis}{steps if direction else -steps},{speed}\n"
            self.ser.write(command.encode())
            self.status.config(text=f"Moving {axis} {'+' if direction else '-'} {steps} steps")
        except ValueError:
            messagebox.showerror("Error", "Invalid step size")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def on_x_slider_move(self, value):
        if not self.slider_moving:
            self.slider_moving = True
            try:
                target_pos = int(float(value))  # Convert slider value to integer
                speed = self.speed_var.get()
                command = f"X:{target_pos},{speed}\n"
                self.ser.write(command.encode())
                self.status.config(text=f"Moving X to {target_pos} steps")
            except serial.SerialException:
                messagebox.showerror("Error", "Serial communication error")
            self.slider_moving = False

    def on_y_slider_move(self, value):
        if not self.slider_moving:
            self.slider_moving = True
            try:
                target_pos = int(float(value))  # Convert slider value to integer
                speed = self.speed_var.get()
                command = f"Y:{target_pos},{speed}\n"
                self.ser.write(command.encode())
                self.status.config(text=f"Moving Y to {target_pos} steps")
            except serial.SerialException:
                messagebox.showerror("Error", "Serial communication error")
            self.slider_moving = False

    def stop(self):
        try:
            self.ser.write("STOP\n".encode())
            # Wait for response with timeout
            start_time = time.time()
            while time.time() - start_time < 1:  # 1-second timeout
                if self.ser.in_waiting:
                    response = self.ser.readline().decode().strip()
                    if response == "Stopped":
                        self.status.config(text="Stopped")
                        return
            self.status.config(text="Stop failed: No response")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")
            self.status.config(text="Stop failed: Serial error")

    def home(self):
        try:
            self.ser.write("HOME\n".encode())
            self.status.config(text="Homing...")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def set_position(self):
        try:
            x_pos = int(self.x_pos_entry.get())
            y_pos = int(self.y_pos_entry.get())
            if x_pos < 0 or x_pos > 8200 or y_pos < 0 or y_pos > 8200:
                raise ValueError("Position must be 0–8200 steps")
            self.ser.write(f"SETX:{x_pos}\n".encode())
            self.ser.write(f"SETY:{y_pos}\n".encode())
            self.status.config(text=f"Position set to X:{x_pos}, Y:{y_pos}")
            self.x_pos_entry.delete(0, tk.END)
            self.y_pos_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Invalid position (use 0–8200)")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def update_position(self):
        while self.running:
            try:
                self.ser.write("POS\n".encode())
                response = self.ser.readline().decode().strip()
                if response.startswith("X:"):
                    x_pos, y_pos = map(int, response.replace("X:", "").replace("Y:", "").split(","))
                    if not self.slider_moving:
                        self.x_pos_var.set(x_pos)
                        self.y_pos_var.set(y_pos)
                    self.pos_label.config(text=f"X: {x_pos}, Y: {y_pos}")
                    status_response = self.ser.readline().decode().strip()
                    if status_response:
                        self.status.config(text=status_response)
                time.sleep(0.5)  # Update every 0.5 seconds
            except (serial.SerialException, ValueError):
                pass

    def __del__(self):
        self.running = False
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = CNCControlGUI(root)
    root.mainloop()