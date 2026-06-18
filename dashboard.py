import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import display_control as dc
import claude_api as ai

# Dashboard window
root = None
running = False

# UI Labels (updated live)
labels = {}


def create_dashboard():
    global root, running

    root = tk.Tk()
    root.title("👁️ EyeGuard Dashboard")
    root.geometry("500x650")
    root.configure(bg="#1a1a2e")
    root.resizable(False, False)

    # -------- TITLE --------
    tk.Label(
        root,
        text="👁️ EyeGuard",
        font=("Helvetica", 22, "bold"),
        bg="#1a1a2e",
        fg="#e94560"
    ).pack(pady=15)

    tk.Label(
        root,
        text="Smart Desktop Eye Monitor",
        font=("Helvetica", 10),
        bg="#1a1a2e",
        fg="#aaaaaa"
    ).pack()

    # -------- STATUS CARD --------
    status_frame = tk.Frame(root, bg="#16213e", padx=20, pady=15)
    status_frame.pack(fill="x", padx=20, pady=10)

    tk.Label(
        status_frame,
        text="📊 Live Stats",
        font=("Helvetica", 12, "bold"),
        bg="#16213e",
        fg="white"
    ).pack(anchor="w")

    # Stats grid
    stats = [
        ("👁️ Blink Rate", "blink_rate", "-- bpm"),
        ("📏 Distance", "distance_status", "--"),
        ("⚡ Strain Score", "strain_score", "--/100"),
        ("⏱️ Session Time", "session_time", "--"),
        ("📷 Camera", "camera_status", "OFF"),
    ]

    for label_text, key, default in stats:
        row = tk.Frame(status_frame, bg="#16213e")
        row.pack(fill="x", pady=3)

        tk.Label(
            row,
            text=label_text,
            font=("Helvetica", 10),
            bg="#16213e",
            fg="#aaaaaa",
            width=18,
            anchor="w"
        ).pack(side="left")

        lbl = tk.Label(
            row,
            text=default,
            font=("Helvetica", 10, "bold"),
            bg="#16213e",
            fg="#4ecca3",
            anchor="w"
        )
        lbl.pack(side="left")
        labels[key] = lbl

    # -------- DISPLAY CONTROLS --------
    control_frame = tk.Frame(root, bg="#16213e", padx=20, pady=15)
    control_frame.pack(fill="x", padx=20, pady=5)

    tk.Label(
        control_frame,
        text="🖥️ Display Controls",
        font=("Helvetica", 12, "bold"),
        bg="#16213e",
        fg="white"
    ).pack(anchor="w", pady=(0, 10))

    # Zoom controls
    zoom_row = tk.Frame(control_frame, bg="#16213e")
    zoom_row.pack(fill="x", pady=3)

    tk.Label(
        zoom_row,
        text="Zoom:",
        bg="#16213e",
        fg="#aaaaaa",
        width=8,
        anchor="w"
    ).pack(side="left")

    tk.Button(
        zoom_row,
        text="🔍+",
        command=dc.zoom_in,
        bg="#e94560",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    tk.Button(
        zoom_row,
        text="🔍-",
        command=dc.zoom_out,
        bg="#e94560",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    tk.Button(
        zoom_row,
        text="Reset",
        command=dc.reset_zoom,
        bg="#444",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    # Font controls
    font_row = tk.Frame(control_frame, bg="#16213e")
    font_row.pack(fill="x", pady=3)

    tk.Label(
        font_row,
        text="Font:",
        bg="#16213e",
        fg="#aaaaaa",
        width=8,
        anchor="w"
    ).pack(side="left")

    tk.Button(
        font_row,
        text="A+",
        command=dc.increase_font,
        bg="#0f3460",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    tk.Button(
        font_row,
        text="A-",
        command=dc.decrease_font,
        bg="#0f3460",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    # Dark mode
    dark_row = tk.Frame(control_frame, bg="#16213e")
    dark_row.pack(fill="x", pady=3)

    tk.Label(
        dark_row,
        text="Theme:",
        bg="#16213e",
        fg="#aaaaaa",
        width=8,
        anchor="w"
    ).pack(side="left")

    tk.Button(
        dark_row,
        text="🌙 Dark",
        command=lambda: dc.toggle_dark_mode(True),
        bg="#0f3460",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    tk.Button(
        dark_row,
        text="☀️ Light",
        command=lambda: dc.toggle_dark_mode(False),
        bg="#0f3460",
        fg="white",
        relief="flat",
        padx=10
    ).pack(side="left", padx=5)

    # -------- AI ADVICE --------
    ai_frame = tk.Frame(root, bg="#16213e", padx=20, pady=15)
    ai_frame.pack(fill="x", padx=20, pady=5)

    tk.Label(
        ai_frame,
        text="🤖 AI Health Advice",
        font=("Helvetica", 12, "bold"),
        bg="#16213e",
        fg="white"
    ).pack(anchor="w")

    labels["advice"] = scrolledtext.ScrolledText(
        ai_frame,
        height=4,
        bg="#0f3460",
        fg="#4ecca3",
        font=("Helvetica", 9),
        relief="flat",
        wrap="word"
    )
    labels["advice"].pack(fill="x", pady=5)
    labels["advice"].insert("end", "Click 'Get Advice' to get AI health tips...")
    labels["advice"].config(state="disabled")

    tk.Button(
        ai_frame,
        text="🤖 Get AI Advice",
        command=request_advice,
        bg="#e94560",
        fg="white",
        relief="flat",
        padx=15,
        pady=5
    ).pack(pady=5)

    # -------- HOTKEY INFO --------
    tk.Label(
        root,
        text="Press Ctrl+Shift+E to toggle camera",
        font=("Helvetica", 9),
        bg="#1a1a2e",
        fg="#666666"
    ).pack(pady=10)

    running = True
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def on_close():
    global running
    running = False
    root.destroy()


# -------- Update Labels from eye_monitor --------
def update_display(data):
    if not running or root is None:
        return

    def _update():
        try:
            # Blink rate
            labels["blink_rate"].config(
                text=f"{data.get('blink_rate', 0)} bpm"
            )

            # Distance
            status = data.get("distance_status", "--")
            color = "#4ecca3" if "Normal" in status else "#e94560"
            labels["distance_status"].config(text=status, fg=color)

            # Strain score
            strain = data.get("strain_score", 0)
            strain_color = "#4ecca3" if strain < 40 else "#ffaa00" if strain < 70 else "#e94560"
            labels["strain_score"].config(
                text=f"{strain}/100",
                fg=strain_color
            )

            # Session time
            secs = data.get("session_time", 0)
            mins = secs // 60
            s = secs % 60
            labels["session_time"].config(text=f"{mins}m {s}s")

            # Camera status
            cam_on = data.get("camera_on", False)
            labels["camera_status"].config(
                text="ON ✅" if cam_on else "OFF ❌",
                fg="#4ecca3" if cam_on else "#e94560"
            )

        except Exception:
            pass

    root.after(0, _update)


# -------- Request AI Advice --------
latest_data = {}

def request_advice():
    def show_advice(text):
        if labels.get("advice"):
            labels["advice"].config(state="normal")
            labels["advice"].delete("1.0", "end")
            labels["advice"].insert("end", text)
            labels["advice"].config(state="disabled")

    labels["advice"].config(state="normal")
    labels["advice"].delete("1.0", "end")
    labels["advice"].insert("end", "Getting AI advice...")
    labels["advice"].config(state="disabled")

    ai.get_advice(latest_data, callback=show_advice)


def set_latest_data(data):
    global latest_data
    latest_data = data


# -------- Start Dashboard in Thread --------
def start():
    threading.Thread(target=create_dashboard, daemon=True).start()
