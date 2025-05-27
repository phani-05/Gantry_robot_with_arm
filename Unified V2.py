import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel, Label, Entry, Button
import serial
import time
import json
import os
import re
import threading

class UnifiedGantryArmGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gantry and Arm Control")
        self.root.geometry("900x900")
        self.root.configure(bg="#f0f0f0")

        # Serial Connections
        try:
            self.gantry_ser = serial.Serial('COM4', 9600, timeout=1)
            self.arm_ser = serial.Serial('COM3', 9600, timeout=1)
            time.sleep(2)
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", f"Failed to connect: {e}")
            self.root.quit()

        # JSON Files
        self.gantry_pos_file = "gantry_positions.json"
        self.gantry_seq_file = "gantry_sequences.json"
        self.arm_pos_file = "arm_positions.json"
        self.arm_seq_file = "arm_sequences.json"
        self.auto_file = "automation_scripts.json"

        # Initialize Data
        self.gantry_positions = self.load_json(self.gantry_pos_file)
        self.gantry_sequences = self.load_json(self.gantry_seq_file)
        self.arm_positions = self.load_json(self.arm_pos_file)
        self.arm_sequences = self.load_json(self.arm_seq_file)
        self.automation_scripts = self.load_json(self.auto_file)

        # GUI Setup
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Gantry Tab
        self.gantry_frame = tk.Frame(self.notebook, bg="#e3f2fd")
        self.notebook.add(self.gantry_frame, text="Gantry")
        self.setup_gantry_tab()

        # Arm Tab
        self.arm_frame = tk.Frame(self.notebook, bg="#c8e6c9")
        self.notebook.add(self.arm_frame, text="Arm")
        self.setup_arm_tab()

        # Automation Tab
        self.auto_frame = tk.Frame(self.notebook, bg="#d1c4e9")
        self.notebook.add(self.auto_frame, text="Automation")
        self.setup_auto_tab()

        # Gantry Update Thread (Arm doesn't need updates since Uno doesn't return positions)
        self.running = True
        self.gantry_slider_moving = False
        self.update_thread = threading.Thread(target=self.update_gantry_positions)
        self.update_thread.daemon = True
        self.update_thread.start()

    def load_json(self, file_path):
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    return json.loads(content) if content else {}
            except json.JSONDecodeError:
                messagebox.showwarning("JSON Error", f"Invalid JSON in {file_path}. Initializing empty.")
        with open(file_path, "w") as f:
            json.dump({}, f)
        return {}

    def save_json(self, data, file_path):
        try:
            with open(file_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {file_path}: {e}")

    # Gantry Tab
    def setup_gantry_tab(self):
        # Axis Control
        axis_frame = tk.Frame(self.gantry_frame, bg="#e3f2fd", bd=2, relief=tk.RAISED)
        axis_frame.pack(fill=tk.X, pady=5)

        tk.Label(axis_frame, text="Axis Control", font=("Helvetica", 12, "bold"), bg="#e3f2fd").pack(pady=5)

        # X Control
        x_frame = tk.Frame(axis_frame, bg="#e3f2fd")
        x_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(x_frame, text="X/Z Axis (0–8200 steps):", bg="#e3f2fd").pack(side=tk.LEFT)
        tk.Button(x_frame, text="X+", command=lambda: self.move_gantry_axis('X', True), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(x_frame, text="X-", command=lambda: self.move_gantry_axis('X', False), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        # X Slider
        self.gantry_x_var = tk.DoubleVar(value=0)
        self.gantry_x_slider = tk.Scale(axis_frame, from_=0, to=8200, orient=tk.HORIZONTAL, variable=self.gantry_x_var,
                                        command=self.on_gantry_x_slider_move, bg="#e3f2fd", length=400)
        self.gantry_x_slider.pack(fill=tk.X, padx=10, pady=5)

        # Y Control
        y_frame = tk.Frame(axis_frame, bg="#e3f2fd")
        y_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(y_frame, text="Y Axis (0–8200 steps):", bg="#e3f2fd").pack(side=tk.LEFT)
        tk.Button(y_frame, text="Y+", command=lambda: self.move_gantry_axis('Y', True), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(y_frame, text="Y-", command=lambda: self.move_gantry_axis('Y', False), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        # Y Slider
        self.gantry_y_var = tk.DoubleVar(value=0)
        self.gantry_y_slider = tk.Scale(axis_frame, from_=0, to=8200, orient=tk.HORIZONTAL, variable=self.gantry_y_var,
                                        command=self.on_gantry_y_slider_move, bg="#e3f2fd", length=400)
        self.gantry_y_slider.pack(fill=tk.X, padx=10, pady=5)

        # Step Size
        step_frame = tk.Frame(axis_frame, bg="#e3f2fd")
        step_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(step_frame, text="Step Size:", bg="#e3f2fd").pack(side=tk.LEFT)
        self.gantry_step_size = tk.Entry(step_frame, width=10)
        self.gantry_step_size.insert(0, "100")
        self.gantry_step_size.pack(side=tk.LEFT, padx=5)

        # Speed
        speed_frame = tk.Frame(self.gantry_frame, bg="#fff9c4", bd=2, relief=tk.RAISED)
        speed_frame.pack(fill=tk.X, pady=5)
        tk.Label(speed_frame, text="Speed (µs, lower=faster):", font=("Helvetica", 12, "bold"), bg="#fff9c4").pack(pady=5)
        self.gantry_speed_var = tk.IntVar(value=500)
        self.gantry_speed_slider = tk.Scale(speed_frame, from_=2000, to=500, orient=tk.HORIZONTAL, variable=self.gantry_speed_var,
                                           bg="#fff9c4", length=400)
        self.gantry_speed_slider.pack(fill=tk.X, padx=10, pady=5)

        # Constraints
        constr_frame = tk.Frame(self.gantry_frame, bg="#d1c4e9", bd=2, relief=tk.RAISED)
        constr_frame.pack(fill=tk.X, pady=5)
        tk.Label(constr_frame, text="Constraints (0–8200)", font=("Helvetica", 12, "bold"), bg="#d1c4e9").pack(pady=5)
        constr_inner = tk.Frame(constr_frame, bg="#d1c4e9")
        constr_inner.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(constr_inner, text="X Min:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.gantry_x_min = tk.Entry(constr_inner, width=8)
        self.gantry_x_min.pack(side=tk.LEFT, padx=5)
        tk.Label(constr_inner, text="X Max:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.gantry_x_max = tk.Entry(constr_inner, width=8)
        self.gantry_x_max.pack(side=tk.LEFT, padx=5)
        tk.Label(constr_inner, text="Y Min:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.gantry_y_min = tk.Entry(constr_inner, width=8)
        self.gantry_y_min.pack(side=tk.LEFT, padx=5)
        tk.Label(constr_inner, text="Y Max:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.gantry_y_max = tk.Entry(constr_inner, width=8)
        self.gantry_y_max.pack(side=tk.LEFT, padx=5)
        tk.Button(constr_inner, text="Set", command=self.set_gantry_constraints, bg="#673ab7", fg="white").pack(side=tk.LEFT, padx=10)

        # Manual Positioning
        pos_frame = tk.Frame(self.gantry_frame, bg="#c8e6c9", bd=2, relief=tk.RAISED)
        pos_frame.pack(fill=tk.X, pady=5)
        tk.Label(pos_frame, text="Manual Positioning", font=("Helvetica", 12, "bold"), bg="#c8e6c9").pack(pady=5)
        pos_inner = tk.Frame(pos_frame, bg="#c8e6c9")
        pos_inner.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(pos_inner, text="X:", bg="#c8e6c9").pack(side=tk.LEFT)
        self.gantry_x_pos = tk.Entry(pos_inner, width=8)
        self.gantry_x_pos.pack(side=tk.LEFT, padx=5)
        tk.Label(pos_inner, text="Y:", bg="#c8e6c9").pack(side=tk.LEFT)
        self.gantry_y_pos = tk.Entry(pos_inner, width=8)
        self.gantry_y_pos.pack(side=tk.LEFT, padx=5)
        tk.Button(pos_inner, text="Set", command=self.set_gantry_position, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)

        # General Controls
        control_frame = tk.Frame(self.gantry_frame, bg="#e3f2fd")
        control_frame.pack(fill=tk.X, pady=10)
        tk.Button(control_frame, text="Home", command=self.gantry_home, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Emergency Stop", command=self.gantry_stop, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

        # Saved Positions
        saved_frame = tk.Frame(self.gantry_frame, bg="#e3f2fd", bd=2, relief=tk.RAISED)
        saved_frame.pack(fill=tk.X, pady=5)
        tk.Label(saved_frame, text="Saved Positions", font=("Helvetica", 12, "bold"), bg="#e3f2fd").pack(pady=5)
        self.gantry_pos_list = tk.Listbox(saved_frame, height=5)
        self.gantry_pos_list.pack(fill=tk.X, padx=10, pady=5)
        saved_buttons = tk.Frame(saved_frame, bg="#e3f2fd")
        saved_buttons.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(saved_buttons, text="Save", command=self.save_gantry_position, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(saved_buttons, text="Load", command=self.load_gantry_position, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(saved_buttons, text="Delete", command=self.delete_gantry_position, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

        # Sequences
        seq_frame = tk.Frame(self.gantry_frame, bg="#d1c4e9", bd=2, relief=tk.RAISED)
        seq_frame.pack(fill=tk.X, pady=5)
        tk.Label(seq_frame, text="Sequences", font=("Helvetica", 12, "bold"), bg="#d1c4e9").pack(pady=5)
        self.gantry_seq_list = tk.Listbox(seq_frame, height=5)
        self.gantry_seq_list.pack(fill=tk.X, padx=10, pady=5)
        seq_buttons = tk.Frame(seq_frame, bg="#d1c4e9")
        seq_buttons.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(seq_buttons, text="Record Step", command=self.record_gantry_step, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(seq_buttons, text="Save Seq", command=self.save_gantry_sequence, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(seq_buttons, text="Load Seq", command=self.load_gantry_sequence, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(seq_buttons, text="Play Seq", command=self.play_gantry_sequence, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(seq_buttons, text="Modify", command=self.modify_gantry_step, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(seq_buttons, text="Delete Step", command=self.delete_gantry_step, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

        # Status
        status_frame = tk.Frame(self.gantry_frame, bg="#e3f2fd")
        status_frame.pack(fill=tk.X, pady=10)
        tk.Label(status_frame, text="Gantry Position:", bg="#e3f2fd").pack()
        self.gantry_pos_label = tk.Label(status_frame, text="X: 0, Y: 0", bg="#e3f2fd")
        self.gantry_pos_label.pack(pady=5)
        self.gantry_status = tk.Label(status_frame, text="Ready", bg="#e3f2fd")
        self.gantry_status.pack(pady=5)

        self.update_gantry_lists()

    # Arm Tab
    def setup_arm_tab(self):
        # Arm-specific variables
        self.recorded_sequence = []
        self.movement_mode = "simultaneous"  # Default to simultaneous movement
        self.movement_mode_enabled = False   # Default to disabled
        self.last_angles = [0] * 6           # Track last sent angles for single motor movement
        self.stop_flag = [False]             # Stop flag for emergency stop
        self.joint_names = ["Base", "Shoulder", "Elbow", "Wrist Tilt", "Wrist Rotate", "Gripper"]

        # Main frame with two columns
        main_frame = tk.Frame(self.arm_frame, bg="#c8e6c9")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left column (main elements)
        left_frame = tk.Frame(main_frame, bg="#c8e6c9")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        left_canvas = tk.Canvas(left_frame, bg="#c8e6c9")
        left_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=left_canvas.yview)
        left_scrollable_frame = tk.Frame(left_canvas, bg="#c8e6c9")

        left_scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )

        left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Servo controls (left column)
        self.sliders = []
        self.angle_labels = []
        for i, joint in enumerate(self.joint_names):
            servo_frame = tk.Frame(left_scrollable_frame, bg="#e3f2fd", bd=2, relief=tk.RAISED)
            servo_frame.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(
                servo_frame,
                text=f"Servo {i} ({joint})",
                font=("Helvetica", 10, "bold"),
                bg="#e3f2fd",
                anchor="w"
            ).pack(fill=tk.X, padx=5, pady=2)

            slider_frame = tk.Frame(servo_frame, bg="#e3f2fd")
            slider_frame.pack(fill=tk.X, padx=5)

            s = tk.Scale(
                slider_frame,
                from_=-30,
                to=30,
                orient=tk.HORIZONTAL,
                resolution=1,
                command=lambda x, idx=i: (
                    self.send_arm_angles([servo.get() for servo in self.sliders], single_motor_index=idx if self.movement_mode_enabled and self.movement_mode == "single" else None),
                    self.update_arm_angle_labels()
                ),
                bg="#e3f2fd",
                troughcolor="#bbdefb",
                length=300
            )
            s.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.sliders.append(s)

            angle_label = tk.Label(slider_frame, text="0°", font=("Helvetica", 10), bg="#e3f2fd")
            angle_label.pack(side=tk.RIGHT, padx=5)
            self.angle_labels.append(angle_label)

        ttk.Separator(left_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Movement mode controls (left column)
        movement_mode_frame = tk.Frame(left_scrollable_frame, bg="#d1c4e9", bd=2, relief=tk.RAISED)
        movement_mode_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            movement_mode_frame,
            text="Movement Mode",
            font=("Helvetica", 10, "bold"),
            bg="#d1c4e9",
            anchor="w"
        ).pack(fill=tk.X, padx=5, pady=2)

        movement_mode_inner_frame = tk.Frame(movement_mode_frame, bg="#d1c4e9")
        movement_mode_inner_frame.pack(fill=tk.X, padx=5, pady=2)

        self.movement_mode_var = tk.IntVar(value=0)
        tk.Checkbutton(
            movement_mode_inner_frame,
            text="Enable Movement Mode",
            variable=self.movement_mode_var,
            command=self.toggle_arm_movement_mode_enabled,
            bg="#d1c4e9",
            font=("Helvetica", 9)
        ).pack(side=tk.LEFT, padx=5)

        self.mode_button = tk.Button(
            movement_mode_inner_frame,
            text="Mode: Simultaneous Movement",
            command=self.toggle_arm_movement_mode,
            bg="#673ab7",
            fg="white",
            font=("Helvetica", 10),
            relief=tk.RAISED,
            state=tk.DISABLED
        )
        self.mode_button.pack(side=tk.LEFT, padx=5)

        ttk.Separator(left_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Control buttons (left column)
        button_frame = tk.Frame(left_scrollable_frame, bg="#c8e6c9", bd=2, relief=tk.RAISED)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            button_frame,
            text="Controls",
            font=("Helvetica", 10, "bold"),
            bg="#c8e6c9",
            anchor="w"
        ).pack(fill=tk.X, padx=5, pady=2)

        buttons = [
            ("Save Position", self.save_arm_position),
            ("Load Position", self.load_arm_position),
            ("Delete Position", self.delete_arm_position),
            ("Record Step", self.record_arm_step),
            ("Playback Sequence", self.play_arm_sequence),
            ("Clear All", self.clear_arm),
            ("Home Position", self.arm_home_position),
            ("Emergency Stop", self.arm_emergency_stop),
            ("Custom Angles (Comma-Separated)", self.arm_custom_angles),
            ("Custom Joint Angles", self.arm_custom_joint_angles)
        ]

        button_grid_frame = tk.Frame(button_frame, bg="#c8e6c9")
        button_grid_frame.pack(fill=tk.X, padx=5, pady=2)

        for idx, (text, cmd) in enumerate(buttons):
            color = "#f44336" if text == "Emergency Stop" else "#4CAF50"
            btn = tk.Button(
                button_grid_frame,
                text=text,
                command=cmd,
                bg=color,
                fg="white",
                font=("Helvetica", 10),
                relief=tk.RAISED
            )
            btn.grid(row=idx // 2, column=idx % 2, padx=5, pady=2, sticky="ew")

        button_grid_frame.grid_columnconfigure(0, weight=1)
        button_grid_frame.grid_columnconfigure(1, weight=1)

        ttk.Separator(left_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Speed control (left column)
        speed_frame = tk.Frame(left_scrollable_frame, bg="#fff9c4", bd=2, relief=tk.RAISED)
        speed_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            speed_frame,
            text="Speed (ms/step, for positions and sequences)",
            font=("Helvetica", 10, "bold"),
            bg="#fff9c4",
            anchor="w"
        ).pack(fill=tk.X, padx=5, pady=2)

        self.arm_speed_slider = tk.Scale(
            speed_frame,
            from_=100,
            to=2000,
            orient=tk.HORIZONTAL,
            resolution=100,
            bg="#fff9c4",
            troughcolor="#ffecb3",
            length=300
        )
        self.arm_speed_slider.set(700)
        self.arm_speed_slider.pack(fill=tk.X, padx=5, pady=2)

        # Right column (manual inputs, saved positions, sequence management)
        right_frame = tk.Frame(main_frame, bg="#c8e6c9")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        right_canvas = tk.Canvas(right_frame, bg="#c8e6c9")
        right_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=right_canvas.yview)
        right_scrollable_frame = tk.Frame(right_canvas, bg="#c8e6c9")

        right_scrollable_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )

        right_canvas.create_window((0, 0), window=right_scrollable_frame, anchor="nw")
        right_canvas.configure(yscrollcommand=right_scrollbar.set)

        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Servo controls with manual input (right column)
        self.manual_entries = []
        self.manual_angle_labels = []
        for i, joint in enumerate(self.joint_names):
            servo_frame = tk.Frame(right_scrollable_frame, bg="#e3f2fd", bd=2, relief=tk.RAISED)
            servo_frame.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(
                servo_frame,
                text=f"Servo {i} ({joint})",
                font=("Helvetica", 10, "bold"),
                bg="#e3f2fd",
                anchor="w"
            ).pack(fill=tk.X, padx=5, pady=2)

            angle_frame = tk.Frame(servo_frame, bg="#e3f2fd")
            angle_frame.pack(fill=tk.X, padx=5)

            angle_label = tk.Label(angle_frame, text="0°", font=("Helvetica", 10), bg="#e3f2fd")
            angle_label.pack(side=tk.RIGHT, padx=5)
            self.manual_angle_labels.append(angle_label)

            input_frame = tk.Frame(servo_frame, bg="#e3f2fd")
            input_frame.pack(fill=tk.X, padx=5, pady=2)

            tk.Label(
                input_frame,
                text="Manual Angle:",
                font=("Helvetica", 9),
                bg="#e3f2fd"
            ).pack(side=tk.LEFT)

            entry = tk.Entry(input_frame, width=5)
            entry.pack(side=tk.LEFT, padx=5)
            self.manual_entries.append(entry)

            tk.Button(
                input_frame,
                text="Save",
                command=lambda idx=i: self.apply_arm_manual_angle(idx),
                bg="#4CAF50",
                fg="white",
                font=("Helvetica", 8)
            ).pack(side=tk.LEFT, padx=5)

        ttk.Separator(right_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Saved positions list (right column)
        positions_frame = tk.Frame(right_scrollable_frame, bg="#c8e6c9")
        positions_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            positions_frame,
            text="Saved Positions",
            font=("Helvetica", 10, "bold"),
            bg="#c8e6c9",
            anchor="w"
        ).pack(fill=tk.X, padx=5, pady=2)

        self.arm_pos_list = tk.Listbox(positions_frame, height=5)
        self.arm_pos_list.pack(fill=tk.X, padx=5, pady=2)

        ttk.Separator(right_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Sequence management (right column)
        sequence_frame = tk.Frame(right_scrollable_frame, bg="#c8e6c9")
        sequence_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            sequence_frame,
            text="Recorded Sequence",
            font=("Helvetica", 10, "bold"),
            bg="#c8e6c9",
            anchor="w"
        ).pack(fill=tk.X, padx=5, pady=2)

        self.arm_seq_list = tk.Listbox(sequence_frame, height=5)
        self.arm_seq_list.pack(fill=tk.X, padx=5, pady=2)

        sequence_buttons_frame = tk.Frame(sequence_frame, bg="#c8e6c9")
        sequence_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

        tk.Button(
            sequence_buttons_frame,
            text="Move Up",
            command=self.move_arm_step_up,
            bg="#2196F3",
            fg="white",
            font=("Helvetica", 8),
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            sequence_buttons_frame,
            text="Move Down",
            command=self.move_arm_step_down,
            bg="#2196F3",
            fg="white",
            font=("Helvetica", 8),
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            sequence_buttons_frame,
            text="Delete Step",
            command=self.delete_arm_step,
            bg="#f44336",
            fg="white",
            font=("Helvetica", 8),
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        # Update lists after all widgets are initialized
        self.update_arm_lists()

    # Automation Tab
    def setup_auto_tab(self):
        # Script Creation
        create_frame = tk.Frame(self.auto_frame, bg="#d1c4e9", bd=2, relief=tk.RAISED)
        create_frame.pack(fill=tk.X, pady=5)
        tk.Label(create_frame, text="Create Automation Script", font=("Helvetica", 12, "bold"), bg="#d1c4e9").pack(pady=5)

        # Action Selection
        action_frame = tk.Frame(create_frame, bg="#d1c4e9")
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(action_frame, text="Action Type:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.action_type = ttk.Combobox(action_frame, values=["Gantry Position", "Arm Sequence"], state="readonly")
        self.action_type.pack(side=tk.LEFT, padx=5)
        tk.Label(action_frame, text="Name:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.action_name = ttk.Combobox(action_frame)
        self.action_name.pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="Add", command=self.add_auto_action, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        # Script List
        script_frame = tk.Frame(self.auto_frame, bg="#d1c4e9")
        script_frame.pack(fill=tk.X, pady=5)
        tk.Label(script_frame, text="Current Script:", bg="#d1c4e9").pack()
        self.auto_script_list = tk.Listbox(script_frame, height=5)
        self.auto_script_list.pack(fill=tk.X, padx=10, pady=5)
        script_buttons = tk.Frame(script_frame, bg="#d1c4e9")
        script_buttons.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(script_buttons, text="Move Up", command=self.move_auto_action_up, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(script_buttons, text="Move Down", command=self.move_auto_action_down, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(script_buttons, text="Delete", command=self.delete_auto_action, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

        # Script Management
        manage_frame = tk.Frame(self.auto_frame, bg="#d1c4e9")
        manage_frame.pack(fill=tk.X, pady=5)
        tk.Label(manage_frame, text="Script Name:", bg="#d1c4e9").pack(side=tk.LEFT)
        self.script_name = tk.Entry(manage_frame, width=20)
        self.script_name.pack(side=tk.LEFT, padx=5)
        tk.Button(manage_frame, text="Save Script", command=self.save_auto_script, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(manage_frame, text="Load Script", command=self.load_auto_script, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(manage_frame, text="Run Script", command=self.run_auto_script, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        # Status
        status_frame = tk.Frame(self.auto_frame, bg="#d1c4e9")
        status_frame.pack(fill=tk.X, pady=10)
        self.auto_status = tk.Label(status_frame, text="Ready", bg="#d1c4e9")
        self.auto_status.pack(pady=5)

        self.current_script = []
        self.update_auto_list()

    # Gantry Methods
    def move_gantry_axis(self, axis, direction):
        try:
            steps = int(self.gantry_step_size.get())
            if steps <= 0:
                raise ValueError("Step size must be positive")
            speed = self.gantry_speed_var.get()
            command = f"{axis}{steps if direction else -steps},{speed}\n"
            self.gantry_ser.write(command.encode())
            self.gantry_status.config(text=f"Moving {axis} {'+' if direction else '-'} {steps} steps")
        except ValueError:
            messagebox.showerror("Error", "Invalid step size")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def on_gantry_x_slider_move(self, value):
        if not self.gantry_slider_moving:
            self.gantry_slider_moving = True
            try:
                target_pos = int(float(value))
                speed = self.gantry_speed_var.get()
                self.gantry_ser.write(f"X:{target_pos},{speed}\n".encode())
                self.gantry_status.config(text=f"Moving X to {target_pos} steps")
            except serial.SerialException:
                messagebox.showerror("Error", "Serial communication error")
            self.gantry_slider_moving = False

    def on_gantry_y_slider_move(self, value):
        if not self.gantry_slider_moving:
            self.gantry_slider_moving = True
            try:
                target_pos = int(float(value))
                speed = self.gantry_speed_var.get()
                self.gantry_ser.write(f"Y:{target_pos},{speed}\n".encode())
                self.gantry_status.config(text=f"Moving Y to {target_pos} steps")
            except serial.SerialException:
                messagebox.showerror("Error", "Serial communication error")
            self.gantry_slider_moving = False

    def gantry_stop(self):
        try:
            self.gantry_ser.write("STOP\n".encode())
            start_time = time.time()
            while time.time() - start_time < 1:
                if self.gantry_ser.in_waiting:
                    response = self.gantry_ser.readline().decode().strip()
                    if response == "Stopped":
                        self.gantry_status.config(text="Emergency Stop")
                        return
            messagebox.showwarning("Warning", "Stop failed: No response")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def gantry_home(self):
        try:
            self.gantry_ser.write("HOME\n".encode())
            self.gantry_status.config(text="Homing...")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def set_gantry_position(self):
        try:
            x_pos = int(self.gantry_x_pos.get())
            y_pos = int(self.gantry_y_pos.get())
            if x_pos < 0 or x_pos > 8200 or y_pos < 0 or y_pos > 8200:
                raise ValueError("Position must be 0–8200")
            self.gantry_ser.write(f"SETX:{x_pos}\n".encode())
            self.gantry_ser.write(f"SETY:{y_pos}\n".encode())
            self.gantry_x_var.set(x_pos)
            self.gantry_y_var.set(y_pos)
            self.gantry_status.config(text=f"Position set to X:{x_pos}, Y:{y_pos}")
            self.gantry_x_pos.delete(0, tk.END)
            self.gantry_y_pos.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Invalid position (0–8200)")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def set_gantry_constraints(self):
        try:
            x_min = int(self.gantry_x_min.get())
            x_max = int(self.gantry_x_max.get())
            y_min = int(self.gantry_y_min.get())
            y_max = int(self.gantry_y_max.get())
            if x_min < 0 or x_max > 8200 or x_min > x_max or y_min < 0 or y_max > 8200 or y_min > y_max:
                raise ValueError("Constraints must be 0 ≤ min ≤ max ≤ 8200")
            self.gantry_ser.write(f"CONX:{x_min},{x_max}\n".encode())
            self.gantry_ser.write(f"CONY:{y_min},{y_max}\n".encode())
            self.gantry_x_slider.config(from_=x_min, to=x_max)
            self.gantry_y_slider.config(from_=y_min, to=y_max)
            self.gantry_status.config(text=f"Constraints set: X:{x_min}-{x_max}, Y:{y_min}-{y_max}")
            for entry in [self.gantry_x_min, self.gantry_x_max, self.gantry_y_min, self.gantry_y_max]:
                entry.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Invalid constraints")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def save_gantry_position(self):
        try:
            name = simpledialog.askstring("Save Position", "Enter name:")
            if not name:
                return
            self.gantry_ser.write("POS\n".encode())
            time.sleep(0.1)
            response = self.gantry_ser.readline().decode().strip()
            if response.startswith("X:"):
                x_pos = int(response[2:response.index(",Y:")])
                y_pos = int(response[response.index(",Y:") + 3:])
                self.gantry_positions[name] = [x_pos, y_pos]
                self.save_json(self.gantry_positions, self.gantry_pos_file)
                self.update_gantry_lists()
                messagebox.showinfo("Success", f"Saved '{name}': X:{x_pos}, Y:{y_pos}")
            else:
                raise ValueError("Invalid response")
        except (ValueError, serial.SerialException) as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def load_gantry_position(self):
        try:
            name = self.gantry_pos_list.get(tk.ACTIVE)
            if not name or name not in self.gantry_positions:
                messagebox.showwarning("Error", "Select a position")
                return
            x_pos, y_pos = self.gantry_positions[name]
            speed = self.gantry_speed_var.get()
            self.gantry_ser.write(f"X:{x_pos},{speed}\n".encode())
            time.sleep(0.1)
            self.gantry_ser.write(f"Y:{y_pos},{speed}\n".encode())
            self.gantry_x_var.set(x_pos)
            self.gantry_y_var.set(y_pos)
            self.gantry_status.config(text=f"Loaded '{name}': X:{x_pos}, Y:{y_pos}")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def delete_gantry_position(self):
        try:
            name = self.gantry_pos_list.get(tk.ACTIVE)
            if not name or name not in self.gantry_positions:
                messagebox.showwarning("Error", "Select a position")
                return
            if messagebox.askyesno("Confirm", f"Delete '{name}'?"):
                del self.gantry_positions[name]
                self.save_json(self.gantry_positions, self.gantry_pos_file)
                self.update_gantry_lists()
                messagebox.showinfo("Deleted", f"'{name}' deleted")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def record_gantry_step(self):
        try:
            self.gantry_ser.write("POS\n".encode())
            time.sleep(0.1)
            response = self.gantry_ser.readline().decode().strip()
            if response.startswith("X:"):
                x_pos = int(response[2:response.index(",Y:")])
                y_pos = int(response[response.index(",Y:") + 3:])
                if not hasattr(self, 'current_gantry_seq'):
                    self.current_gantry_seq = []
                self.current_gantry_seq.append([x_pos, y_pos])
                self.update_gantry_lists()
                messagebox.showinfo("Recorded", f"Step {len(self.current_gantry_seq)}: X:{x_pos}, Y:{y_pos}")
            else:
                raise ValueError("Invalid response")
        except (ValueError, serial.SerialException) as e:
            messagebox.showerror("Error", f"Failed to record: {e}")

    def save_gantry_sequence(self):
        if not hasattr(self, 'current_gantry_seq') or not self.current_gantry_seq:
            messagebox.showwarning("Error", "No sequence to save")
            return
        name = simpledialog.askstring("Save Sequence", "Enter name:")
        if name:
            self.gantry_sequences[name] = self.current_gantry_seq
            self.save_json(self.gantry_sequences, self.gantry_seq_file)
            self.current_gantry_seq = []
            self.update_gantry_lists()
            messagebox.showinfo("Success", f"Sequence '{name}' saved")

    def load_gantry_sequence(self):
        name = self.gantry_seq_list.get(tk.ACTIVE)
        if not name or name not in self.gantry_sequences:
            messagebox.showwarning("Error", "Select a sequence")
            return
        self.current_gantry_seq = self.gantry_sequences[name]
        self.update_gantry_lists()
        messagebox.showinfo("Loaded", f"Sequence '{name}' loaded")

    def play_gantry_sequence(self):
        if not hasattr(self, 'current_gantry_seq') or not self.current_gantry_seq:
            messagebox.showwarning("Error", "No sequence loaded")
            return
        try:
            speed = self.gantry_speed_var.get()
            for step in self.current_gantry_seq:
                x_pos, y_pos = step
                self.gantry_ser.write(f"X:{x_pos},{speed}\n".encode())
                time.sleep(0.1)
                self.gantry_ser.write(f"Y:{y_pos},{speed}\n".encode())
                self.gantry_x_var.set(x_pos)
                self.gantry_y_var.set(y_pos)
                self.gantry_status.config(text=f"Playing: X:{x_pos}, Y:{y_pos}")
                self.root.update()
                time.sleep(speed / 1000000.0)
            self.gantry_status.config(text="Playback complete")
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def modify_gantry_step(self):
        selected = self.gantry_seq_list.curselection()
        if not selected or not hasattr(self, 'current_gantry_seq'):
            messagebox.showwarning("Error", "Select a step")
            return
        index = selected[0]
        dialog = Toplevel(self.root)
        dialog.title("Modify Step")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        x_pos, y_pos = self.current_gantry_seq[index]
        tk.Label(dialog, text="X Position:").pack(pady=5)
        x_entry = tk.Entry(dialog)
        x_entry.insert(0, str(x_pos))
        x_entry.pack(pady=5)
        tk.Label(dialog, text="Y Position:").pack(pady=5)
        y_entry = tk.Entry(dialog)
        y_entry.insert(0, str(y_pos))
        y_entry.pack(pady=5)

        def apply():
            try:
                new_x = int(x_entry.get())
                new_y = int(y_entry.get())
                if new_x < 0 or new_x > 8200 or new_y < 0 or new_y > 8200:
                    raise ValueError("Positions must be 0–8200")
                self.current_gantry_seq[index] = [new_x, new_y]
                self.update_gantry_lists()
                self.gantry_seq_list.selection_set(index)
                messagebox.showinfo("Success", f"Step {index+1} modified")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Invalid positions (0–8200)")

        tk.Button(dialog, text="Apply", command=apply, bg="#4CAF50", fg="white").pack(pady=10)
        tk.Button(dialog, text="Cancel", command=dialog.destroy, bg="#f44336", fg="white").pack(pady=5)

    def delete_gantry_step(self):
        selected = self.gantry_seq_list.curselection()
        if not selected or not hasattr(self, 'current_gantry_seq'):
            messagebox.showwarning("Error", "Select a step")
            return
        index = selected[0]
        if messagebox.askyesno("Confirm", f"Delete Step {index+1}?"):
            self.current_gantry_seq.pop(index)
            self.update_gantry_lists()
            messagebox.showinfo("Deleted", f"Step {index+1} deleted")

    # Arm Methods
    def send_arm_angles(self, angles, single_motor_index=None):
        """Send specified angles to Arduino, handling simultaneous or single motor movement."""
        if self.movement_mode_enabled and self.movement_mode == "single" and single_motor_index is not None:
            send_angles = self.last_angles.copy()
            send_angles[single_motor_index] = angles[single_motor_index]
        else:
            send_angles = angles
        angle_str = ",".join(map(str, send_angles)) + "\n"
        try:
            self.arm_ser.write(angle_str.encode())
            self.last_angles = send_angles  # Update last sent angles
        except serial.SerialException:
            messagebox.showerror("Error", "Serial communication error")

    def move_to_arm_angles(self, target_angles, speed_ms, sequential=False):
        """Smoothly transition to target angles with specified speed, optionally moving one motor at a time."""
        current_angles = [servo.get() for servo in self.sliders]
        steps = 20
        step_delay = speed_ms // steps

        if sequential and self.movement_mode_enabled and self.movement_mode == "single":
            for motor_idx in range(len(current_angles)):
                if self.stop_flag[0]:
                    return
                start_angle = current_angles[motor_idx]
                end_angle = target_angles[motor_idx]
                for step in range(steps + 1):
                    if self.stop_flag[0]:
                        return
                    angle = start_angle + (end_angle - start_angle) * step / steps
                    interpolated_angles = current_angles.copy()
                    interpolated_angles[motor_idx] = int(round(angle))
                    self.sliders[motor_idx].set(min(max(interpolated_angles[motor_idx], -30), 30))
                    self.send_arm_angles(interpolated_angles, single_motor_index=motor_idx)
                    self.update_arm_angle_labels()
                    self.root.update()
                    time.sleep(step_delay / 1000.0)
                current_angles[motor_idx] = target_angles[motor_idx]
        else:
            for step in range(steps + 1):
                if self.stop_flag[0]:
                    return
                interpolated_angles = []
                for i in range(len(current_angles)):
                    angle = current_angles[i] + (target_angles[i] - current_angles[i]) * step / steps
                    interpolated_angles.append(int(round(angle)))
                    self.sliders[i].set(min(max(interpolated_angles[i], -30), 30))
                self.send_arm_angles(interpolated_angles)
                self.update_arm_angle_labels()
                self.root.update()
                time.sleep(step_delay / 1000.0)

    def toggle_arm_movement_mode(self):
        """Toggle between simultaneous and single motor movement."""
        self.movement_mode = "single" if self.movement_mode == "simultaneous" else "simultaneous"
        self.mode_button.config(text=f"Mode: {self.movement_mode.capitalize()} Movement")

    def toggle_arm_movement_mode_enabled(self):
        """Enable or disable the movement mode."""
        self.movement_mode_enabled = self.movement_mode_var.get() == 1
        self.mode_button.config(state=tk.NORMAL if self.movement_mode_enabled else tk.DISABLED)

    def save_arm_position(self):
        """Save current servo positions with a user-defined name."""
        name = simpledialog.askstring("Save Position", "Enter position name:")
        if name:
            self.arm_positions[name] = [servo.get() for servo in self.sliders]
            self.save_json(self.arm_positions, self.arm_pos_file)
            self.update_arm_lists()
            messagebox.showinfo("Success", f"Saved position '{name}'")

    def load_arm_position(self):
        """Load a saved position and apply it with speed control."""
        name = self.arm_pos_list.get(tk.ACTIVE)
        if name and name in self.arm_positions:
            target_angles = self.arm_positions[name]
            speed_ms = int(self.arm_speed_slider.get())
            self.move_to_arm_angles(target_angles, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")

    def delete_arm_position(self):
        """Delete the selected saved position."""
        name = self.arm_pos_list.get(tk.ACTIVE)
        if name and name in self.arm_positions:
            if messagebox.askyesno("Confirm Delete", f"Delete position '{name}'?"):
                del self.arm_positions[name]
                self.save_json(self.arm_positions, self.arm_pos_file)
                self.update_arm_lists()
                messagebox.showinfo("Deleted", f"Position '{name}' deleted.")

    def record_arm_step(self):
        """Record current servo positions as a step in the sequence."""
        self.recorded_sequence.append([servo.get() for servo in self.sliders])
        self.update_arm_lists()
        messagebox.showinfo("Recorded", f"Step {len(self.recorded_sequence)} recorded.")

    def play_arm_sequence(self):
        """Play back recorded sequence with adjustable speed, optionally moving one motor at a time."""
        speed_ms = int(self.arm_speed_slider.get())
        for step in self.recorded_sequence:
            if self.stop_flag[0]:
                break
            self.move_to_arm_angles(step, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")

    def clear_arm(self):
        """Reset all sliders to 0 and send to Arduino."""
        target_angles = [0] * 6
        speed_ms = int(self.arm_speed_slider.get())
        self.move_to_arm_angles(target_angles, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")

    def arm_home_position(self):
        """Set all servos to 0° (home position)."""
        target_angles = [0] * 6
        speed_ms = int(self.arm_speed_slider.get())
        self.move_to_arm_angles(target_angles, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")
        messagebox.showinfo("Home", "Returned to home position (0°).")

    def arm_emergency_stop(self):
        """Halt all movement and return to home position."""
        self.stop_flag[0] = True
        self.arm_home_position()
        messagebox.showwarning("Emergency Stop", "All movements stopped.")
        self.stop_flag[0] = False

    def arm_custom_angles(self):
        """Prompt user for custom angles via comma-separated input."""
        input_str = simpledialog.askstring(
            "Custom Angles",
            "Enter 6 angles separated by commas (e.g., -10,20,0,15,-5,30):"
        )
        if input_str:
            try:
                angles = [float(x) for x in re.split(r',\s*', input_str.strip())]
                if len(angles) != 6:
                    raise ValueError("Exactly 6 angles required.")
                speed_ms = int(self.arm_speed_slider.get())
                self.move_to_arm_angles(angles, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")
                messagebox.showinfo("Success", "Custom angles applied.")
            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Error: {e}")

    def arm_custom_joint_angles(self):
        """Open a dialog for individual joint angle inputs."""
        dialog = Toplevel(self.root)
        dialog.title("Custom Joint Angles")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()

        entries = []
        for i, joint in enumerate(self.joint_names):
            Label(dialog, text=f"{joint} Angle:", font=("Helvetica", 10)).pack(pady=5)
            entry = Entry(dialog)
            entry.pack(pady=5)
            entries.append(entry)

        def apply_angles():
            try:
                angles = []
                for i, entry in enumerate(entries):
                    value = entry.get().strip()
                    if not value:
                        raise ValueError(f"{self.joint_names[i]} angle is empty.")
                    angle = float(value)
                    angles.append(angle)
                speed_ms = int(self.arm_speed_slider.get())
                self.move_to_arm_angles(angles, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")
                messagebox.showinfo("Success", "Custom joint angles applied.")
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Error: {e}")

        Button(dialog, text="Apply", command=apply_angles, bg="#4CAF50", fg="white").pack(pady=10)
        Button(dialog, text="Cancel", command=dialog.destroy, bg="#f44336", fg="white").pack(pady=5)

    def apply_arm_manual_angle(self, index):
        """Apply angle from manual input box to the corresponding slider."""
        try:
            value = self.manual_entries[index].get().strip()
            if not value:
                raise ValueError("Angle is empty.")
            angle = float(value)
            self.sliders[index].set(min(max(angle, -30), 30))
            current_angles = [servo.get() for servo in self.sliders]
            self.send_arm_angles(current_angles, single_motor_index=index if self.movement_mode_enabled and self.movement_mode == "single" else None)
            self.update_arm_angle_labels()
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error for {self.joint_names[index]}: {e}")

    def move_arm_step_up(self):
        """Move the selected step up in the sequence."""
        selected = self.arm_seq_list.curselection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a step to move.")
            return
        index = selected[0]
        if index == 0:
            return
        self.recorded_sequence[index], self.recorded_sequence[index-1] = self.recorded_sequence[index-1], self.recorded_sequence[index]
        self.update_arm_lists()
        self.arm_seq_list.selection_set(index-1)

    def move_arm_step_down(self):
        """Move the selected step down in the sequence."""
        selected = self.arm_seq_list.curselection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a step to move.")
            return
        index = selected[0]
        if index == len(self.recorded_sequence) - 1:
            return
        self.recorded_sequence[index], self.recorded_sequence[index+1] = self.recorded_sequence[index+1], self.recorded_sequence[index]
        self.update_arm_lists()
        self.arm_seq_list.selection_set(index+1)

    def delete_arm_step(self):
        """Delete the selected step from the sequence."""
        selected = self.arm_seq_list.curselection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a step to delete.")
            return
        index = selected[0]
        if messagebox.askyesno("Confirm Delete", f"Delete Step {index+1}?"):
            self.recorded_sequence.pop(index)
            self.update_arm_lists()
            messagebox.showinfo("Deleted", f"Step {index+1} deleted.")

    def update_arm_angle_labels(self):
        """Update labels to show current slider angles."""
        for i, label in enumerate(self.angle_labels):
            label.config(text=f"{self.sliders[i].get()}°")
        for i, label in enumerate(self.manual_angle_labels):
            label.config(text=f"{self.sliders[i].get()}°")

    # Automation Methods
    def add_auto_action(self):
        action_type = self.action_type.get()
        name = self.action_name.get()
        if not action_type or not name:
            messagebox.showwarning("Error", "Select action type and name")
            return
        type_key = "gantry_pos" if action_type == "Gantry Position" else "arm_seq"
        data = self.gantry_positions if type_key == "gantry_pos" else self.arm_sequences
        if name not in data:
            messagebox.showwarning("Error", f"'{name}' not found")
            return
        self.current_script.append({"type": type_key, "name": name})
        self.update_auto_list()

    def move_auto_action_up(self):
        selected = self.auto_script_list.curselection()
        if not selected:
            return
        index = selected[0]
        if index == 0:
            return
        self.current_script[index], self.current_script[index-1] = self.current_script[index-1], self.current_script[index]
        self.update_auto_list()
        self.auto_script_list.selection_set(index-1)

    def move_auto_action_down(self):
        selected = self.auto_script_list.curselection()
        if not selected:
            return
        index = selected[0]
        if index == len(self.current_script) - 1:
            return
        self.current_script[index], self.current_script[index+1] = self.current_script[index+1], self.current_script[index]
        self.update_auto_list()
        self.auto_script_list.selection_set(index+1)

    def delete_auto_action(self):
        selected = self.auto_script_list.curselection()
        if not selected:
            return
        index = selected[0]
        if messagebox.askyesno("Confirm", f"Delete action {index+1}?"):
            self.current_script.pop(index)
            self.update_auto_list()

    def save_auto_script(self):
        if not self.current_script:
            messagebox.showwarning("Error", "No script to save")
            return
        name = self.script_name.get()
        if not name:
            messagebox.showwarning("Error", "Enter script name")
            return
        self.automation_scripts[name] = self.current_script
        self.save_json(self.automation_scripts, self.auto_file)
        self.current_script = []
        self.script_name.delete(0, tk.END)
        self.update_auto_list()
        messagebox.showinfo("Success", f"Script '{name}' saved")

    def load_auto_script(self):
        name = simpledialog.askstring("Load Script", "Enter script name:")
        if name and name in self.automation_scripts:
            self.current_script = self.automation_scripts[name]
            self.update_auto_list()
            messagebox.showinfo("Loaded", f"Script '{name}' loaded")
        else:
            messagebox.showwarning("Error", "Script not found")

    def run_auto_script(self):
        if not self.current_script:
            messagebox.showwarning("Error", "No script loaded")
            return
        try:
            for action in self.current_script:
                action_type = action["type"]
                name = action["name"]
                if action_type == "gantry_pos":
                    if name not in self.gantry_positions:
                        raise ValueError(f"Gantry position '{name}' not found")
                    x_pos, y_pos = self.gantry_positions[name]
                    speed = self.gantry_speed_var.get()
                    self.gantry_ser.write(f"X:{x_pos},{speed}\n".encode())
                    time.sleep(0.1)
                    self.gantry_ser.write(f"Y:{y_pos},{speed}\n".encode())
                    start_time = time.time()
                    while time.time() - start_time < 2:
                        if self.gantry_ser.in_waiting:
                            response = self.gantry_ser.readline().decode().strip()
                            if response.startswith("X:") and f"Y:{y_pos}" in response:
                                break
                    self.gantry_x_var.set(x_pos)
                    self.gantry_y_var.set(y_pos)
                    self.auto_status.config(text=f"Gantry moved to '{name}'")
                elif action_type == "arm_seq":
                    if name not in self.arm_sequences:
                        raise ValueError(f"Arm sequence '{name}' not found")
                    speed_ms = int(self.arm_speed_slider.get())
                    for step in self.arm_sequences[name]:
                        self.move_to_arm_angles(step, speed_ms, sequential=self.movement_mode_enabled and self.movement_mode == "single")
                        self.auto_status.config(text=f"Playing arm step: {step}")
                        self.root.update()
                    self.auto_status.config(text=f"Arm sequence '{name}' completed")
                self.root.update()
            self.auto_status.config(text="Script complete")
        except (ValueError, serial.SerialException) as e:
            messagebox.showerror("Error", f"Automation failed: {e}")

    # Update Methods
    def update_gantry_lists(self):
        self.gantry_pos_list.delete(0, tk.END)
        for name in self.gantry_positions:
            self.gantry_pos_list.insert(tk.END, name)
        self.gantry_seq_list.delete(0, tk.END)
        if hasattr(self, 'current_gantry_seq'):
            for i, step in enumerate(self.current_gantry_seq):
                self.gantry_seq_list.insert(tk.END, f"Step {i+1}: X={step[0]}, Y={step[1]}")

    def update_arm_lists(self):
        self.arm_pos_list.delete(0, tk.END)
        for name in self.arm_positions:
            self.arm_pos_list.insert(tk.END, name)
        self.arm_seq_list.delete(0, tk.END)
        for i, step in enumerate(self.recorded_sequence):
            self.arm_seq_list.insert(tk.END, f"Step {i+1}: {step}")

    def update_auto_list(self):
        self.auto_script_list.delete(0, tk.END)
        for i, action in enumerate(self.current_script):
            action_type = "Gantry Position" if action["type"] == "gantry_pos" else "Arm Sequence"
            self.auto_script_list.insert(tk.END, f"Action {i+1}: {action_type} - {action['name']}")
        self.action_name['values'] = list(self.gantry_positions.keys()) if self.action_type.get() == "Gantry Position" else list(self.arm_sequences.keys())

    def update_gantry_positions(self):
        while self.running:
            try:
                self.gantry_ser.write("POS\n".encode())
                response = self.gantry_ser.readline().decode().strip()
                if response.startswith("X:"):
                    x_pos = int(response[2:response.index(",Y:")])
                    y_pos = int(response[response.index(",Y:") + 3:])
                    if not self.gantry_slider_moving:
                        self.gantry_x_var.set(x_pos)
                        self.gantry_y_var.set(y_pos)
                    self.gantry_pos_label.config(text=f"X: {x_pos}, Y: {y_pos}")
                time.sleep(0.5)
            except (serial.SerialException, ValueError):
                pass

    def __del__(self):
        self.running = False
        for ser in [self.gantry_ser, self.arm_ser]:
            if ser.is_open:
                ser.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = UnifiedGantryArmGUI(root)
    try:
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        print("Serial connections closed.")