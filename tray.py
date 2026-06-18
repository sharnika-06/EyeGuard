import pystray
from PIL import Image, ImageDraw
import threading
import os

tray_icon = None
dashboard_started = False


# -------- Create Icon --------
def create_icon():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=(26, 26, 46, 255))
    draw.ellipse([8, 20, 56, 44], fill=(78, 204, 163, 255))
    draw.ellipse([22, 26, 42, 38], fill=(26, 26, 46, 255))
    draw.ellipse([27, 29, 37, 35], fill=(233, 69, 96, 255))
    return img


# -------- Menu Actions --------
def open_dashboard(icon, item):
    global dashboard_started
    if not dashboard_started:
        import dashboard
        threading.Thread(target=dashboard.create_dashboard, daemon=True).start()
        dashboard_started = True


def toggle_cam(icon, item):
    import eye_monitor
    eye_monitor.toggle_camera()


def quit_app(icon, item):
    icon.stop()
    os._exit(0)


# -------- Start Tray --------
def start():
    global tray_icon

    icon_image = create_icon()

    menu = pystray.Menu(
        pystray.MenuItem("👁️ EyeGuard", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("📊 Open Dashboard", open_dashboard),
        pystray.MenuItem("📷 Toggle Camera (Ctrl+Shift+E)", toggle_cam),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Quit", quit_app)
    )

    tray_icon = pystray.Icon(
        "EyeGuard",
        icon_image,
        "👁️ EyeGuard",
        menu
    )

    print("System tray started!")
    tray_icon.run()
