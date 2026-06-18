import time

import eye_monitor
import display_control
import claude_api
import data_collector
import dashboard
import tray
import train_model
import os 
CLAUDE_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ── Config — change CURRENT_USER when a different member uses the app ──────────
CURRENT_USER   = "member1"   # change to member2 / member3 etc. when needed

# ── Load zoom ML model ─────────────────────────────────────────────────────────
zoom_model = train_model.load_models()

# ── Note: zoom is now handled inside eye_monitor.py directly ──────────────────
# eye_monitor detects movement and calls display_control.zoom_in/out itself.
# main.py no longer needs to intercept zoom — it just passes data to dashboard
# and data_collector.


def on_eye_data(data):
    # Update dashboard
    dashboard.update_display(data)
    dashboard.set_latest_data(data)

    # Save to CSV
    data_collector.update_data(data)


def main():
    print("=" * 40)
    print("  EyeGuard Starting...")
    print("=" * 40)

    data_collector.set_user(CURRENT_USER)
    claude_api.init_client(CLAUDE_API_KEY)
    data_collector.init_csv()
    data_collector.start_auto_save()

    eye_monitor.on_data_update = on_eye_data
    eye_monitor.start()
    dashboard.start()

    time.sleep(1)

    rows     = data_collector.get_row_count()
    per_user = data_collector.get_rows_per_user()

    print(f"  User       : {CURRENT_USER}")
    print(f"  Total rows : {rows}")
    print(f"  Per user   : {per_user}")
    print(f"  Zoom       : movement-based (Ctrl+Plus/Minus hotkeys)")
    print(f"  ML model   : {'loaded — trained on real user data' if zoom_model else 'not found'}")
    print(f"  Dark mode  : coming later")
    print("=" * 40)
    print("  Ctrl+Shift+E → toggle camera")
    print("  Zoom resets to 100% when camera turns OFF")
    print("=" * 40 + "\n")

    tray.start()


if __name__ == "__main__":
    main()
