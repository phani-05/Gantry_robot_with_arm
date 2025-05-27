import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel, Label, Entry, Button, ttk
import serial
import json
import os
import re
import time

# Set up serial communication
try:
    arduino = serial.Serial('COM3', 9600, timeout=1)
except Exception as e:
    messagebox.showerror("Serial Error", f"Failed to connect to COM3: {e}")
    exit()

# Load saved positions
SAVE_FILE = "saved_positions.json"
saved_positions = {}
if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE, "r") as f:
            content = f.read().strip()
            if content:
                saved_positions = json.loads(content)
            else:
                with open(SAVE_FILE, "w") as f:
                    json.dump({}, f)
    except (json.JSONDecodeError, ValueError) as e:
        messagebox.showwarning(
            "JSON Error",
            f"Invalid JSON in {SAVE_FILE}: {e}. Initializing empty positions."
        )
        with open(SAVE_FILE, "w") as f:
            json.dump({}, f)
else:
    with open(SAVE_FILE, "w") as f:
        json.dump({}, f)

recorded_sequence = []
movement_mode = "simultaneous"  # Default to simultaneous movement
movement_mode_enabled = False   # Default to disabled
last_angles = [0] * 6           # Track last sent angles for single motor movement

def send_angles(angles, single_motor_index=None):
    """Send specified angles to Arduino, handling simultaneous or single motor movement."""
    global last_angles
    if movement_mode_enabled and movement_mode == "single" and single_motor_index is not None:
        # In single motor mode, only send the changed motor's angle
        send_angles = last_angles.copy()
        send_angles[single_motor_index] = angles[single_motor_index]
    else:
        # In simultaneous mode or when mode is disabled, send all angles
        send_angles = angles
    angle_str = ",".join(map(str, send_angles)) + "\n"
    arduino.write(angle_str.encode())
    last_angles = send_angles  # Update last sent angles

def move_to_angles(target_angles, speed_ms, sequential=False):
    """Smoothly transition to target angles with specified speed, optionally moving one motor at a time."""
    current_angles = [servo.get() for servo in sliders]
    steps = 20
    step_delay = speed_ms // steps

    if sequential and movement_mode_enabled and movement_mode == "single":
        # Move one motor at a time
        for motor_idx in range(len(current_angles)):
            if stop_flag[0]:
                return
            start_angle = current_angles[motor_idx]
            end_angle = target_angles[motor_idx]
            for step in range(steps + 1):
                if stop_flag[0]:
                    return
                angle = start_angle + (end_angle - start_angle) * step / steps
                interpolated_angles = current_angles.copy()
                interpolated_angles[motor_idx] = int(round(angle))
                sliders[motor_idx].set(min(max(interpolated_angles[motor_idx], -45), 45))
                send_angles(interpolated_angles, single_motor_index=motor_idx)
                update_angle_labels()
                root.update()
                time.sleep(step_delay / 1000.0)
            current_angles[motor_idx] = target_angles[motor_idx]  # Update current angles for next motor
    else:
        # Move all motors simultaneously
        for step in range(steps + 1):
            if stop_flag[0]:
                return
            interpolated_angles = []
            for i in range(len(current_angles)):
                angle = current_angles[i] + (target_angles[i] - current_angles[i]) * step / steps
                interpolated_angles.append(int(round(angle)))
                sliders[i].set(min(max(interpolated_angles[i], -45), 45))
            send_angles(interpolated_angles)
            update_angle_labels()
            root.update()
            time.sleep(step_delay / 1000.0)

def toggle_movement_mode():
    """Toggle between simultaneous and single motor movement."""
    global movement_mode
    movement_mode = "single" if movement_mode == "simultaneous" else "simultaneous"
    mode_button.config(text=f"Mode: {movement_mode.capitalize()} Movement")

def toggle_movement_mode_enabled():
    """Enable or disable the movement mode."""
    global movement_mode_enabled
    movement_mode_enabled = movement_mode_var.get() == 1
    mode_button.config(state=tk.NORMAL if movement_mode_enabled else tk.DISABLED)

def save_position():
    """Save current servo positions with a user-defined name."""
    name = simpledialog.askstring("Save Position", "Enter position name:")
    if name:
        saved_positions[name] = [servo.get() for servo in sliders]
        with open(SAVE_FILE, "w") as f:
            json.dump(saved_positions, f)
        update_position_list()

def load_position():
    """Load a saved position and apply it with speed control."""
    name = position_list.get(tk.ACTIVE)
    if name and name in saved_positions:
        target_angles = saved_positions[name]
        speed_ms = int(speed_slider.get())
        move_to_angles(target_angles, speed_ms, sequential=movement_mode_enabled and movement_mode == "single")

def delete_position():
    """Delete the selected saved position."""
    name = position_list.get(tk.ACTIVE)
    if name and name in saved_positions:
        if messagebox.askyesno("Confirm Delete", f"Delete position '{name}'?"):
            del saved_positions[name]
            with open(SAVE_FILE, "w") as f:
                json.dump(saved_positions, f)
            update_position_list()
            messagebox.showinfo("Deleted", f"Position '{name}' deleted.")

def record_step():
    """Record current servo positions as a step in the sequence."""
    recorded_sequence.append([servo.get() for servo in sliders])
    update_sequence_list()
    messagebox.showinfo("Recorded", f"Step {len(recorded_sequence)} recorded.")

def playback():
    """Play back recorded sequence with adjustable speed, optionally moving one motor at a time."""
    speed_ms = int(speed_slider.get())
    for step in recorded_sequence:
        if stop_flag[0]:
            break
        move_to_angles(step, speed_ms, sequential=movement_mode_enabled and movement_mode == "single")

def clear_all():
    """Reset all sliders to 0 and send to Arduino."""
    target_angles = [0] * 6
    speed_ms = int(speed_slider.get())
    move_to_angles(target_angles, speed_ms, sequential=movement_mode_enabled and movement_mode == "single")

def home_position():
    """Set all servos to 0° (home position)."""
    target_angles = [0] * 6
    speed_ms = int(speed_slider.get())
    move_to_angles(target_angles, speed_ms, sequential=movement_mode_enabled and movement_mode == "single")
    messagebox.showinfo("Home", "Returned to home position (0°).")

def emergency_stop():
    """Halt all movement and return to home position."""
    stop_flag[0] = True
    home_position()
    messagebox.showwarning("Emergency Stop", "All movements stopped.")
    stop_flag[0] = False

def custom_angles():
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
            speed_ms = int(speed_slider.get())
            move_to_angles(angles, speed_ms, sequential=movement_mode_enabled and movement_mode == "single")
            messagebox.showinfo("Success", "Custom angles applied.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error: {e}")

def custom_joint_angles():
    """Open a dialog for individual joint angle inputs."""
    dialog = Toplevel(root)
    dialog.title("Custom Joint Angles")
    dialog.geometry("300x400")
    dialog.transient(root)
    dialog.grab_set()

    entries = []
    for i, joint in enumerate(joint_names):
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
                    raise ValueError(f"{joint_names[i]} angle is empty.")
                angle = float(value)
                angles.append(angle)
            speed_ms = int(speed_slider.get())
            move_to_angles(angles, speed_ms, sequential=movement_mode_enabled and movement_mode == "single")
            messagebox.showinfo("Success", "Custom joint angles applied.")
            dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error: {e}")

    Button(dialog, text="Apply", command=apply_angles, bg="#4CAF50", fg="white").pack(pady=10)
    Button(dialog, text="Cancel", command=dialog.destroy, bg="#f44336", fg="white").pack(pady=5)

def apply_manual_angle(index):
    """Apply angle from manual input box to the corresponding slider."""
    try:
        value = manual_entries[index].get().strip()
        if not value:
            raise ValueError("Angle is empty.")
        angle = float(value)
        sliders[index].set(min(max(angle, -45), 45))
        current_angles = [servo.get() for servo in sliders]
        send_angles(current_angles, single_motor_index=index if movement_mode_enabled and movement_mode == "single" else None)
        update_angle_labels()
    except ValueError as e:
        messagebox.showerror("Invalid Input", f"Error for {joint_names[index]}: {e}")

def update_position_list():
    """Update the listbox with saved position names."""
    position_list.delete(0, tk.END)
    for name in saved_positions:
        position_list.insert(tk.END, name)

def update_sequence_list():
    """Update the listbox with recorded sequence steps."""
    sequence_list.delete(0, tk.END)
    for i, step in enumerate(recorded_sequence):
        sequence_list.insert(tk.END, f"Step {i+1}: {step}")

def move_step_up():
    """Move the selected step up in the sequence."""
    selected = sequence_list.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a step to move.")
        return
    index = selected[0]
    if index == 0:
        return
    recorded_sequence[index], recorded_sequence[index-1] = recorded_sequence[index-1], recorded_sequence[index]
    update_sequence_list()
    sequence_list.selection_set(index-1)

def move_step_down():
    """Move the selected step down in the sequence."""
    selected = sequence_list.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a step to move.")
        return
    index = selected[0]
    if index == len(recorded_sequence) - 1:
        return
    recorded_sequence[index], recorded_sequence[index+1] = recorded_sequence[index+1], recorded_sequence[index]
    update_sequence_list()
    sequence_list.selection_set(index+1)

def delete_step():
    """Delete the selected step from the sequence."""
    selected = sequence_list.curselection()
    if not selected:
        messagebox.showwarning("Selection Error", "Please select a step to delete.")
        return
    index = selected[0]
    if messagebox.askyesno("Confirm Delete", f"Delete Step {index+1}?"):
        recorded_sequence.pop(index)
        update_sequence_list()
        messagebox.showinfo("Deleted", f"Step {index+1} deleted.")

def update_angle_labels():
    """Update labels to show current slider angles."""
    for i, label in enumerate(angle_labels):
        label.config(text=f"{sliders[i].get()}°")
    for i, label in enumerate(manual_angle_labels):
        label.config(text=f"{sliders[i].get()}°")

# GUI Setup
root = tk.Tk()
root.title("Robotic Arm Controller")
root.geometry("900x600")
root.configure(bg="#f0f0f0")

# Define joint names
joint_names = ["Base", "Shoulder", "Elbow", "Wrist Tilt", "Wrist Rotate", "Gripper"]

# Main frame with two columns
main_frame = tk.Frame(root, bg="#f0f0f0")
main_frame.pack(fill=tk.BOTH, expand=True)

# Left column (main elements)
left_frame = tk.Frame(main_frame, bg="#f0f0f0")
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

left_canvas = tk.Canvas(left_frame, bg="#f0f0f0")
left_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=left_canvas.yview)
left_scrollable_frame = tk.Frame(left_canvas, bg="#f0f0f0")

left_scrollable_frame.bind(
    "<Configure>",
    lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
)

left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
left_canvas.configure(yscrollcommand=left_scrollbar.set)

left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Stop flag for emergency stop
stop_flag = [False]

# Servo controls (left column)
sliders = []
angle_labels = []
for i, joint in enumerate(joint_names):
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
        from_=-45,
        to=45,
        orient=tk.HORIZONTAL,
        resolution=1,
        command=lambda x, idx=i: (
            send_angles([servo.get() for servo in sliders], single_motor_index=idx if movement_mode_enabled and movement_mode == "single" else None),
            update_angle_labels()
        ),
        bg="#e3f2fd",
        troughcolor="#bbdefb",
        length=300
    )
    s.pack(side=tk.LEFT, fill=tk.X, expand=True)
    sliders.append(s)

    angle_label = tk.Label(slider_frame, text="0°", font=("Helvetica", 10), bg="#e3f2fd")
    angle_label.pack(side=tk.RIGHT, padx=5)
    angle_labels.append(angle_label)

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

movement_mode_var = tk.IntVar(value=0)
tk.Checkbutton(
    movement_mode_inner_frame,
    text="Enable Movement Mode",
    variable=movement_mode_var,
    command=toggle_movement_mode_enabled,
    bg="#d1c4e9",
    font=("Helvetica", 9)
).pack(side=tk.LEFT, padx=5)

mode_button = tk.Button(
    movement_mode_inner_frame,
    text="Mode: Simultaneous Movement",
    command=toggle_movement_mode,
    bg="#673ab7",
    fg="white",
    font=("Helvetica", 10),
    relief=tk.RAISED,
    state=tk.DISABLED
)
mode_button.pack(side=tk.LEFT, padx=5)

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
    ("Save Position", save_position),
    ("Load Position", load_position),
    ("Delete Position", delete_position),
    ("Record Step", record_step),
    ("Playback Sequence", playback),
    ("Clear All", clear_all),
    ("Home Position", home_position),
    ("Emergency Stop", emergency_stop),
    ("Custom Angles (Comma-Separated)", custom_angles),
    ("Custom Joint Angles", custom_joint_angles)
]

# Arrange buttons in a 2-column grid
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

# Configure grid column weights for even spacing
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

speed_slider = tk.Scale(
    speed_frame,
    from_=100,
    to=2000,
    orient=tk.HORIZONTAL,
    resolution=100,
    bg="#fff9c4",
    troughcolor="#ffecb3",
    length=300
)
speed_slider.set(700)
speed_slider.pack(fill=tk.X, padx=5, pady=2)

# Right column (manual inputs, saved positions, sequence management)
right_frame = tk.Frame(main_frame, bg="#f0f0f0")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

right_canvas = tk.Canvas(right_frame, bg="#f0f0f0")
right_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=right_canvas.yview)
right_scrollable_frame = tk.Frame(right_canvas, bg="#f0f0f0")

right_scrollable_frame.bind(
    "<Configure>",
    lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
)

right_canvas.create_window((0, 0), window=right_scrollable_frame, anchor="nw")
right_canvas.configure(yscrollcommand=right_scrollbar.set)

right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Servo controls with manual input (right column)
manual_entries = []
manual_angle_labels = []
for i, joint in enumerate(joint_names):
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
    manual_angle_labels.append(angle_label)

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
    manual_entries.append(entry)

    tk.Button(
        input_frame,
        text="Save",
        command=lambda idx=i: apply_manual_angle(idx),
        bg="#4CAF50",
        fg="white",
        font=("Helvetica", 8)
    ).pack(side=tk.LEFT, padx=5)

ttk.Separator(right_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

# Saved positions list (right column)
positions_frame = tk.Frame(right_scrollable_frame, bg="#f0f0f0")
positions_frame.pack(fill=tk.X, padx=10, pady=5)

tk.Label(
    positions_frame,
    text="Saved Positions",
    font=("Helvetica", 10, "bold"),
    bg="#f0f0f0",
    anchor="w"
).pack(fill=tk.X, padx=5, pady=2)

position_list = tk.Listbox(positions_frame, height=5)
position_list.pack(fill=tk.X, padx=5, pady=2)

update_position_list()

ttk.Separator(right_scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=10)

# Sequence management (right column)
sequence_frame = tk.Frame(right_scrollable_frame, bg="#f0f0f0")
sequence_frame.pack(fill=tk.X, padx=10, pady=5)

tk.Label(
    sequence_frame,
    text="Recorded Sequence",
    font=("Helvetica", 10, "bold"),
    bg="#f0f0f0",
    anchor="w"
).pack(fill=tk.X, padx=5, pady=2)

sequence_list = tk.Listbox(sequence_frame, height=5)
sequence_list.pack(fill=tk.X, padx=5, pady=2)

sequence_buttons_frame = tk.Frame(sequence_frame, bg="#f0f0f0")
sequence_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

tk.Button(
    sequence_buttons_frame,
    text="Move Up",
    command=move_step_up,
    bg="#2196F3",
    fg="white",
    font=("Helvetica", 8),
    relief=tk.RAISED
).pack(side=tk.LEFT, padx=2)

tk.Button(
    sequence_buttons_frame,
    text="Move Down",
    command=move_step_down,
    bg="#2196F3",
    fg="white",
    font=("Helvetica", 8),
    relief=tk.RAISED
).pack(side=tk.LEFT, padx=2)

tk.Button(
    sequence_buttons_frame,
    text="Delete Step",
    command=delete_step,
    bg="#f44336",
    fg="white",
    font=("Helvetica", 8),
    relief=tk.RAISED
).pack(side=tk.LEFT, padx=2)

update_sequence_list()

try:
    root.mainloop()
except Exception as e:
    messagebox.showerror("Error", f"An error occurred: {e}")
finally:
    if arduino.is_open:
        arduino.close()
        print("Serial connection closed.")