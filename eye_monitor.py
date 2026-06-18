import cv2
import mediapipe as mp
import numpy as np
import threading
import time
import keyboard
import warnings
import os
import logging
from plyer import notification
import display_control

# ── Suppress warnings ─────────────────────────────────────────────────────────
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('mediapipe').setLevel(logging.CRITICAL)

# ── Mediapipe ─────────────────────────────────────────────────────────────────
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh()

# ── Camera state ──────────────────────────────────────────────────────────────
cap = None
camera_on = False
toggle_lock = False

# ── Blink tracking ────────────────────────────────────────────────────────────
last_blink_time = time.time()
last_alert_time = 0
blink_count = 0
blink_rate = 0
blink_cooldown_flag = False
blink_start_time = time.time()

# ── Face / distance tracking ──────────────────────────────────────────────────
face_width = 0
distance_status = "Normal"
strain_score = 0
session_start = time.time()
last_strain_alert = 0

# ── Movement-based zoom tracking ──────────────────────────────────────────────
# Smoothing buffer — averages last N frames to reduce jitter
SMOOTH_SIZE       = 10     # frames to average
MOVE_THRESHOLD    = 25     # pixels of smooth-width change to trigger zoom
ZOOM_COOLDOWN     = 3.0    # seconds between zoom actions

face_width_history   = []
previous_smooth_width = None   # reference point — set on first stable reading
last_zoom_action_time = 0

# ── Callback set by main.py ───────────────────────────────────────────────────
on_data_update = None


# ── EAR calculation ───────────────────────────────────────────────────────────
def calculate_EAR(eye):
    v1 = np.linalg.norm(eye[1] - eye[5])
    v2 = np.linalg.norm(eye[2] - eye[4])
    h  = np.linalg.norm(eye[0] - eye[3])
    if h == 0:
        return 0
    return (v1 + v2) / (2.0 * h)


# ── Strain score ──────────────────────────────────────────────────────────────
def calculate_strain():
    global strain_score
    score = 0
    if blink_rate < 8:
        score += 40
    elif blink_rate < 12:
        score += 20
    if face_width > 280:
        score += 30
    elif face_width > 220:
        score += 15
    session_mins = (time.time() - session_start) / 60
    if session_mins > 40:
        score += 30
    elif session_mins > 20:
        score += 15
    strain_score = min(score, 100)
    return strain_score


# ── Alerts ────────────────────────────────────────────────────────────────────
def blink_alert():
    notification.notify(
        title="EyeGuard",
        message="You haven't blinked in 10 seconds! Please blink.",
        timeout=3
    )

def strain_alert():
    notification.notify(
        title="EyeGuard — Eye Strain!",
        message=f"Strain score: {strain_score}/100. Take a break!",
        timeout=5
    )


# ── Toggle camera ─────────────────────────────────────────────────────────────
def toggle_camera():
    global camera_on, cap, toggle_lock, session_start
    global face_width_history, previous_smooth_width, last_zoom_action_time

    if toggle_lock:
        return
    toggle_lock = True

    camera_on = not camera_on

    if camera_on:
        cap = cv2.VideoCapture(0)
        session_start = time.time()

        # Reset all movement tracking for fresh session
        face_width_history    = []
        previous_smooth_width = None
        last_zoom_action_time = 0

        print("Camera ON — alerts start in 10 seconds")
        notification.notify(
            title="EyeGuard",
            message="Eye monitoring started!",
            timeout=2
        )
    else:
        if cap is not None:
            cap.release()
            cap = None
        cv2.destroyAllWindows()

        # ── Reset zoom to 100% when camera turns OFF ──────────────────────────
        display_control.reset_zoom()

        # Reset movement tracking
        face_width_history    = []
        previous_smooth_width = None
        last_zoom_action_time = 0

        print("Camera OFF — zoom reset to 100%")
        notification.notify(
            title="EyeGuard",
            message="Eye monitoring stopped. Zoom reset to 100%!",
            timeout=2
        )

    time.sleep(0.5)
    toggle_lock = False


# ── Hotkey ────────────────────────────────────────────────────────────────────
keyboard.add_hotkey('ctrl+shift+e', toggle_camera)


# ── Camera loop ───────────────────────────────────────────────────────────────
def run_camera():
    global last_blink_time, last_alert_time
    global face_width, distance_status
    global blink_count, blink_rate, blink_cooldown_flag
    global blink_start_time, last_strain_alert
    global face_width_history, previous_smooth_width, last_zoom_action_time

    ALERT_GRACE = 10   # seconds after camera ON before alerts fire

    while True:
        if not camera_on:
            time.sleep(0.2)
            continue

        if cap is None or not cap.isOpened():
            time.sleep(0.2)
            continue

        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:

                h, w, _ = frame.shape

                # ── Blink detection ───────────────────────────────────────────
                left_eye_idx = [33, 160, 158, 133, 153, 144]
                eye_pts = [np.array([
                    int(face_landmarks.landmark[i].x * w),
                    int(face_landmarks.landmark[i].y * h)
                ]) for i in left_eye_idx]

                ear = calculate_EAR(eye_pts)

                if ear < 0.25 and not blink_cooldown_flag:
                    blink_count += 1
                    last_blink_time = time.time()
                    blink_cooldown_flag = True
                if ear >= 0.25:
                    blink_cooldown_flag = False

                elapsed = time.time() - blink_start_time
                if elapsed >= 60:
                    blink_rate      = blink_count
                    blink_count     = 0
                    blink_start_time = time.time()
                else:
                    blink_rate = int(blink_count * (60 / max(elapsed, 1)))

                # ── Face width (distance proxy) ───────────────────────────────
                p1 = face_landmarks.landmark[234]
                p2 = face_landmarks.landmark[454]
                x1, y1 = int(p1.x * w), int(p1.y * h)
                x2, y2 = int(p2.x * w), int(p2.y * h)
                face_width = np.linalg.norm(np.array([x1, y1]) - np.array([x2, y2]))

                # Smooth over last SMOOTH_SIZE frames
                face_width_history.append(face_width)
                if len(face_width_history) > SMOOTH_SIZE:
                    face_width_history.pop(0)
                smooth_width = float(np.mean(face_width_history))

                # Distance status label
                if face_width > 280:
                    distance_status = "Too Close"
                elif face_width < 150:
                    distance_status = "Too Far"
                else:
                    distance_status = "Normal"

                # ── MOVEMENT-ONLY ZOOM ────────────────────────────────────────
                # Only zoom when the user physically moves — not while sitting still.
                # We compare current smooth_width to the previous reference.
                # If the change exceeds MOVE_THRESHOLD → zoom and update reference.
                # If still sitting still → reference stays the same → no zoom.
                now = time.time()

                if previous_smooth_width is None:
                    # First stable reading — set reference, no zoom
                    if len(face_width_history) >= SMOOTH_SIZE:
                        previous_smooth_width = smooth_width
                        print(f"Reference set: face_width = {smooth_width:.1f}")
                else:
                    change = smooth_width - previous_smooth_width

                    if abs(change) > MOVE_THRESHOLD:
                        if now - last_zoom_action_time >= ZOOM_COOLDOWN:
                            if change > 0:
                                # Face got bigger → user moved CLOSER → zoom out
                                display_control.zoom_out()
                            else:
                                # Face got smaller → user moved FARTHER → zoom in
                                display_control.zoom_in()
                            last_zoom_action_time = now

                        # Update reference to current position after any movement
                        previous_smooth_width = smooth_width

                # ── Strain ────────────────────────────────────────────────────
                calculate_strain()

                # ── Alerts (only after grace period) ─────────────────────────
                if time.time() - session_start >= ALERT_GRACE:
                    if time.time() - last_blink_time > 10:
                        if time.time() - last_alert_time > 3:
                            threading.Thread(target=blink_alert, daemon=True).start()
                            last_alert_time = time.time()

                    if strain_score > 60:
                        if time.time() - last_strain_alert > 300:
                            threading.Thread(target=strain_alert, daemon=True).start()
                            last_strain_alert = time.time()

                # ── Send data to dashboard ────────────────────────────────────
                if on_data_update:
                    on_data_update({
                        "blink_rate":      blink_rate,
                        "face_width":      round(face_width, 1),
                        "distance_status": distance_status,
                        "strain_score":    strain_score,
                        "session_time":    int(time.time() - session_start),
                        "camera_on":       camera_on
                    })

        cv2.imshow("EyeGuard Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            toggle_camera()


# ── Start ─────────────────────────────────────────────────────────────────────
def start():
    threading.Thread(target=run_camera, daemon=True).start()
    print("EyeGuard eye monitor started!")
    print("Press Ctrl+Shift+E to toggle camera")