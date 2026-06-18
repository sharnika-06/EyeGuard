import csv
import os
import time
import threading
from datetime import datetime

DATA_FILE = "data/eye_data.csv"

os.makedirs("data", exist_ok=True)

HEADERS = [
    "timestamp",
    "user_id",
    "blink_rate",
    "face_width",
    "distance_status",
    "strain_score",
    "session_time"
]

CURRENT_USER = "member1"


def set_user(user_id):
    global CURRENT_USER
    CURRENT_USER = user_id
    print(f"Data collection user set to: {CURRENT_USER}")


def clean_status(status):
    """Strip emojis from distance_status before saving."""
    return (status
            .replace("Too Close \u26a0\ufe0f", "Too Close")
            .replace("Too Far \u26a0\ufe0f", "Too Far")
            .replace("Normal \u2705", "Normal")
            .replace("\u26a0\ufe0f", "")
            .replace("\u2705", "")
            .strip())


def repair_csv():
    """
    Reads every row and keeps only valid ones.
    Fixes: manually deleted rows leaving bad state, encoding issues,
    incomplete rows, or duplicate headers.
    """
    if not os.path.exists(DATA_FILE):
        return

    good_rows = []
    bad_count = 0

    try:
        with open(DATA_FILE, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    continue  # skip header — we write our own
                if len(row) != len(HEADERS):
                    bad_count += 1
                    continue
                if row[0] == "timestamp":  # duplicate header row
                    continue
                good_rows.append(row)
    except Exception as e:
        print(f"Repair read error: {e}")
        return

    try:
        with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(good_rows)
        if bad_count > 0:
            print(f"CSV repaired — removed {bad_count} bad rows, kept {len(good_rows)} good rows")
        else:
            print(f"CSV OK — {len(good_rows)} rows loaded")
    except Exception as e:
        print(f"Repair write error: {e}")


def init_csv():
    """Create CSV if missing, or repair if it already exists."""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
        print(f"Data file created: {DATA_FILE}")
        return

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

        if 'user_id' not in first_line:
            # Old format — backup and recreate
            os.rename(DATA_FILE, DATA_FILE.replace('.csv', '_backup.csv'))
            with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)
            print("CSV updated with user_id column (old file backed up)")
        else:
            # File exists with correct headers — repair any bad rows
            repair_csv()

    except Exception as e:
        print(f"CSV check error: {e} — recreating file")
        backup = DATA_FILE.replace('.csv', '_broken_backup.csv')
        try:
            os.rename(DATA_FILE, backup)
            print(f"Broken CSV backed up to: {backup}")
        except Exception:
            pass
        with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
        print("Fresh CSV created")


def save_data(data):
    """Append one row safely. Auto-repairs file if header is missing."""
    try:
        if not os.path.exists(DATA_FILE):
            init_csv()

        # Check header is present before appending
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        if first_line != ','.join(HEADERS):
            repair_csv()

        with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                CURRENT_USER,
                data.get("blink_rate", 0),
                round(data.get("face_width", 0), 1),
                clean_status(data.get("distance_status", "Unknown")),
                data.get("strain_score", 0),
                data.get("session_time", 0)
            ])
    except Exception as e:
        print(f"Data save error: {e}")
        try:
            repair_csv()
            print("CSV auto-recovered after save error")
        except Exception:
            pass


def get_row_count():
    try:
        if not os.path.exists(DATA_FILE):
            return 0
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f) - 1
    except Exception:
        return 0


def get_rows_per_user():
    try:
        if not os.path.exists(DATA_FILE):
            return {}
        counts = {}
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row.get("user_id", "unknown")
                counts[uid] = counts.get(uid, 0) + 1
        return counts
    except Exception:
        return {}


def get_today_stats():
    try:
        if not os.path.exists(DATA_FILE):
            return {}
        today = datetime.now().strftime("%Y-%m-%d")
        blink_rates, strain_scores = [], []
        too_close_count = 0
        total_rows = 0

        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["timestamp"].startswith(today):
                    try:
                        blink_rates.append(float(row["blink_rate"]))
                        strain_scores.append(float(row["strain_score"]))
                        if "Too Close" in row.get("distance_status", ""):
                            too_close_count += 1
                        total_rows += 1
                    except ValueError:
                        continue

        if total_rows == 0:
            return {}

        return {
            "avg_blink_rate": round(sum(blink_rates) / len(blink_rates), 1),
            "avg_strain": round(sum(strain_scores) / len(strain_scores), 1),
            "total_time": total_rows,
            "too_close_count": too_close_count
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {}


last_data = {}


def start_auto_save():
    def save_loop():
        while True:
            time.sleep(30)
            if last_data and last_data.get("camera_on"):
                save_data(last_data)
                total = get_row_count()
                per_user = get_rows_per_user()
                print(f"Data saved — total rows: {total} | per user: {per_user}")

    threading.Thread(target=save_loop, daemon=True).start()
    print(f"Auto data collection started! Saving every 30s for user: {CURRENT_USER}")


def update_data(data):
    global last_data
    last_data = data
