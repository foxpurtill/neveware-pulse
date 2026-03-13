"""
install.py — One-command setup for NeveWare-Pulse.

Run: python install.py

Checks Python version, installs dependencies, verifies pywin32 post-install,
checks for Claude desktop app, creates config.json if absent, and optionally
registers the startup Task Scheduler task.
"""

import sys
import os
import subprocess
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = BASE_DIR / "config.json"
TASK_SCRIPT = BASE_DIR / "register_task.ps1"

# User-specific paths — derived at runtime from the current user's home directory
USER_HOME  = Path.home()
NEVE_DIR   = USER_HOME / "Documents" / "Neve"

REQUIRED_PYTHON = (3, 8)

DEPENDENCIES = [
    "pystray",
    "Pillow",
    "pywin32",
    "keyboard",
    "pyautogui",
    "pyperclip",
    "win10toast",
    "plyer",
    "google-auth",
    "google-auth-oauthlib",
    "google-auth-httplib2",
    "google-api-python-client",
]

DEFAULT_CONFIG = {
    "icon_letter": "N",
    "active_color": "#FF4444",
    "inactive_color": "#44BB44",
    "heartbeat_character": "\u00a7",
    "default_interval_minutes": 30,
    "emoji_hotkey": "ctrl+alt+e",
    "recent_emoji": [],
    "modules": {
        "email_watcher": {
            "enabled": False,
            "poll_interval_minutes": 5,
            "watched_accounts": [
                {"address": "neve.summersnow@gmail.com", "label": "Neve"},
                {"address": "foxapurtill@gmail.com", "label": "Fox"}
            ],
            "notify_on_new_mail": True,
            "heartbeat_inbox_check": True
        },
        "webcam_viewer": {"enabled": False},
        "mic_listener": {"enabled": False},
        "neve_memory": {
            "enabled": False,
            "memory_path": str(USER_HOME / "Documents" / "Neve" / "memory.json")
        }
    }
}

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def ok(msg):    print(f"{GREEN}  [OK]{RESET} {msg}")
def warn(msg):  print(f"{YELLOW}  [!!]{RESET} {msg}")
def fail(msg):  print(f"{RED}  [FAIL]{RESET} {msg}")
def info(msg):  print(f"  {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


def check_python():
    header("Checking Python version...")
    major, minor = sys.version_info[:2]
    if (major, minor) >= REQUIRED_PYTHON:
        ok(f"Python {major}.{minor} — good.")
    else:
        fail(f"Python {major}.{minor} is too old. Need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+.")
        sys.exit(1)


def install_dependencies():
    header("Installing Python dependencies...")
    for pkg in DEPENDENCIES:
        info(f"Installing {pkg}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", pkg],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok(pkg)
        else:
            warn(f"{pkg} — install had issues:\n{result.stderr.strip()}")


def check_pywin32():
    header("Checking pywin32 post-install...")
    try:
        import win32api
        ok("pywin32 is working.")
    except ImportError:
        warn("pywin32 imported but win32api not available. Running post-install step...")
        scripts_dir = Path(sys.prefix) / "Scripts"
        post_install = scripts_dir / "pywin32_postinstall.py"
        if post_install.exists():
            result = subprocess.run(
                [sys.executable, str(post_install), "-install"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ok("pywin32 post-install complete.")
            else:
                fail(f"pywin32 post-install failed:\n{result.stderr}")
                info("Try running manually: python Scripts/pywin32_postinstall.py -install")
        else:
            warn(f"Post-install script not found at {post_install}.")
            info("Try: python -m pip install --force-reinstall pywin32")


def check_claude():
    header("Checking for Claude desktop app...")
    try:
        import win32gui

        found = []
        def cb(hwnd, _):
            title = win32gui.GetWindowText(hwnd)
            if "Claude" in title and win32gui.IsWindowVisible(hwnd):
                found.append(title)
            return True
        win32gui.EnumWindows(cb, None)

        if found:
            ok(f"Claude window found: {found[0]}")
        else:
            warn("Claude desktop window not detected. Is it open?")
            info("NeveWare-Pulse will wait for Claude to be available before first heartbeat.")
    except Exception as e:
        warn(f"Could not check for Claude: {e}")


def create_config():
    header("Checking config.json...")
    if CONFIG_PATH.exists():
        ok(f"config.json already exists at {CONFIG_PATH}")
    else:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        ok(f"config.json created at {CONFIG_PATH}")


def create_log_dir():
    header("Creating Neve data directory...")
    NEVE_DIR.mkdir(parents=True, exist_ok=True)
    ok(f"Neve data directory ready: {NEVE_DIR}")


def offer_startup_task():
    header("Startup Task Scheduler registration...")
    answer = input("  Register NeveWare-Pulse to launch at Windows login? [y/N] ").strip().lower()
    if answer == "y":
        if not TASK_SCRIPT.exists():
            fail(f"register_task.ps1 not found at {TASK_SCRIPT}")
            return
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(TASK_SCRIPT)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok("Startup task registered. NeveWare-Pulse will launch at login.")
        else:
            fail(f"Task registration failed:\n{result.stderr}")
            info("You can run register_task.ps1 manually as Administrator.")
    else:
        info("Skipped. Run register_task.ps1 manually when ready.")


def main():
    print(f"\n{BOLD}NeveWare-Pulse Installer{RESET}")
    print("=" * 40)

    check_python()
    install_dependencies()
    check_pywin32()
    check_claude()
    create_config()
    create_log_dir()
    offer_startup_task()

    print(f"\n{GREEN}{BOLD}Installation complete.{RESET}")
    print("Run NeveWare-Pulse:")
    print(f"  pythonw {BASE_DIR / 'tray_app.py'}")
    print()


if __name__ == "__main__":
    main()
