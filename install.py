"""
install.py — NeveWare-Pulse guided installer.

Usage:
    python install.py            # Full interactive wizard
    python install.py --silent   # Accept all defaults, no prompts
"""

import sys, os, subprocess, json, shutil, argparse
from pathlib import Path

BASE_DIR   = Path(__file__).parent.resolve()
ASSETS_DIR = BASE_DIR / "assets"

REQUIRED_PYTHON = (3, 8)

# ── ANSI colours (stripped on Windows if not supported) ──────────────────────
def _ansi():
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7)
        return True
    except Exception:
        return False

USE_COLOUR = _ansi()
GREEN  = "\033[92m" if USE_COLOUR else ""
YELLOW = "\033[93m" if USE_COLOUR else ""
RED    = "\033[91m" if USE_COLOUR else ""
CYAN   = "\033[96m" if USE_COLOUR else ""
BOLD   = "\033[1m"  if USE_COLOUR else ""
DIM    = "\033[2m"  if USE_COLOUR else ""
RESET  = "\033[0m"  if USE_COLOUR else ""

def ok(msg):     print(f"  {GREEN}✓{RESET}  {msg}")
def warn(msg):   print(f"  {YELLOW}⚠{RESET}  {msg}")
def err(msg):    print(f"  {RED}✗{RESET}  {msg}")
def info(msg):   print(f"     {DIM}{msg}{RESET}")
def section(msg):print(f"\n{BOLD}{CYAN}{msg}{RESET}\n{'─'*50}")
def banner():
    print(f"""
{BOLD}{CYAN}
  ███╗   ██╗███████╗██╗   ██╗███████╗██╗    ██╗ █████╗ ██████╗ ███████╗
  ████╗  ██║██╔════╝██║   ██║██╔════╝██║    ██║██╔══██╗██╔══██╗██╔════╝
  ██╔██╗ ██║█████╗  ██║   ██║█████╗  ██║ █╗ ██║███████║██████╔╝█████╗
  ██║╚██╗██║██╔══╝  ╚██╗ ██╔╝██╔══╝  ██║███╗██║██╔══██║██╔══██╗██╔══╝
  ██║ ╚████║███████╗ ╚████╔╝ ███████╗╚███╔███╔╝██║  ██║██║  ██║███████╗
  ╚═╝  ╚═══╝╚══════╝  ╚═══╝  ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
                       P U L S E   —   DI Heartbeat Tool{RESET}
""")

def ask(prompt, default="", secret=False):
    """Prompt with default shown. Returns stripped answer or default."""
    display = f"[{default}] " if default else ""
    full = f"  {CYAN}?{RESET}  {prompt} {DIM}{display}{RESET}: "
    if secret:
        import getpass
        val = getpass.getpass(full).strip()
    else:
        val = input(full).strip()
    return val if val else default

def ask_yn(prompt, default=True):
    hint = "[Y/n]" if default else "[y/N]"
    val = input(f"  {CYAN}?{RESET}  {prompt} {DIM}{hint}{RESET} ").strip().lower()
    if not val:   return default
    return val.startswith("y")

def ask_path(prompt, default):
    val = ask(prompt, str(default))
    return Path(val)

# ── Dependency list ──────────────────────────────────────────────────────────
DEPENDENCIES = [
    "pystray", "Pillow", "pywin32", "keyboard",
    "pyautogui", "pyperclip", "plyer",
    "google-auth", "google-auth-oauthlib",
    "google-auth-httplib2", "google-api-python-client",
]

# ── Default install path ─────────────────────────────────────────────────────
DEFAULT_INSTALL = Path("C:/FoxPur-Studios/NeveWare-Pulse")

# ── Step 1: Python version ───────────────────────────────────────────────────
def step_python():
    section("Step 1 — Python version")
    major, minor = sys.version_info[:2]
    if (major, minor) >= REQUIRED_PYTHON:
        ok(f"Python {major}.{minor}")
    else:
        err(f"Python {major}.{minor} is too old. Need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+.")
        sys.exit(1)

# ── Step 2: Install location ─────────────────────────────────────────────────
def step_location(silent):
    section("Step 2 — Install location")
    info(f"Default: {DEFAULT_INSTALL}")
    if silent:
        target = DEFAULT_INSTALL
        info(f"Silent mode — using default: {target}")
    else:
        print()
        use_default = ask_yn(f"Install to {BOLD}{DEFAULT_INSTALL}{RESET}?", default=True)
        if use_default:
            target = DEFAULT_INSTALL
        else:
            target = ask_path("Enter install path", DEFAULT_INSTALL)

    target = Path(target).resolve()

    if target != BASE_DIR:
        if target.exists() and any(target.iterdir()):
            warn(f"Directory exists and has files: {target}")
            if not silent and not ask_yn("Install here anyway?", default=False):
                err("Installation cancelled.")
                sys.exit(0)
        target.mkdir(parents=True, exist_ok=True)
        info(f"Copying files to {target} ...")
        for item in BASE_DIR.iterdir():
            if item.name in {".git", "__pycache__", "*.pyc"}:
                continue
            dest = target / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        ok(f"Files installed to {target}")
    else:
        ok(f"Running from install location — no copy needed")

    return target

# ── Step 3: Dependencies ─────────────────────────────────────────────────────
def step_deps():
    section("Step 3 — Python dependencies")
    for pkg in DEPENDENCIES:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", pkg],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok(pkg)
        else:
            warn(f"{pkg} — possible issue:\n{result.stderr.strip()[:120]}")
    # pywin32 post-install
    try:
        import win32api
        ok("pywin32 — ready")
    except ImportError:
        scripts = Path(sys.prefix) / "Scripts" / "pywin32_postinstall.py"
        if scripts.exists():
            subprocess.run([sys.executable, str(scripts), "-install"],
                           capture_output=True, text=True)
            ok("pywin32 — post-install complete")
        else:
            warn("pywin32 — post-install script not found, may need manual fix")


# ── Step 4: Identity setup ───────────────────────────────────────────────────
def step_identity(silent):
    section("Step 4 — DI Identity")
    info("These set your DI's name, email, and voice. All optional — configure later in Settings.")
    info(f"{DIM}Note: Pulse works by injecting prompts into the Claude desktop app directly.")
    info(f"A Claude API key is NOT required. Pulse uses the app, not the API.{RESET}")
    print()

    if silent:
        return {
            "ai_name": "Neve",
            "icon_letter": "N",
            "email_address": "",
            "elevenlabs_voice_id": "",
            "elevenlabs_api_key": "",
        }

    ai_name      = ask("Your DI's name", "Neve")
    icon_letter  = ask("Tray icon letter", ai_name[0].upper() if ai_name else "N")
    email        = ask("DI email address (for email_watcher module)", "")
    el_voice_id  = ask("ElevenLabs Voice ID (leave blank to skip)", "")
    if el_voice_id:
        print(f"  {DIM}Your API key will be stored only in config.json on this machine.")
        print(f"  ElevenLabs API keys look like: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        print(f"  Paste your key below (the sk- prefix will be handled automatically).{RESET}")
        el_api_key = ask("ElevenLabs API key (paste with Ctrl+V, leave blank to skip)", "")
        # Strip sk- prefix if user included it — ElevenLabs only needs the hex portion
        if el_api_key.lower().startswith("sk-"):
            el_api_key = el_api_key[3:]
    else:
        el_api_key = ""

    return {
        "ai_name":            ai_name,
        "icon_letter":        icon_letter[:1].upper() if icon_letter else "N",
        "email_address":      email,
        "elevenlabs_voice_id": el_voice_id,
        "elevenlabs_api_key":  el_api_key,
    }

# ── Step 5: Module selection ─────────────────────────────────────────────────
MODULES_MENU = [
    ("email_watcher", "Email Watcher",
     "Check inbox on each heartbeat, show toast on new mail"),
    ("voice_output",  "Voice Output",
     "Speak DI responses aloud via ElevenLabs TTS + ffplay"),
    ("webcam_viewer", "Webcam Viewer",
     "Open webcam feed from tray menu (requires webcam MCP server)"),
    ("mic_listener",  "Mic Listener",
     "Listen via microphone, inject spoken context via Whisper"),
]

def step_modules(silent):
    section("Step 5 — Modules")
    info("Choose which optional modules to enable. You can change these later in Settings.")
    print()

    enabled = {}
    if silent:
        # Safe defaults — only things that work without extra setup
        for key, _, _ in MODULES_MENU:
            enabled[key] = key in {"email_watcher"}
        return enabled

    for key, label, desc in MODULES_MENU:
        info(f"{DIM}{desc}{RESET}")
        enabled[key] = ask_yn(f"  Enable {BOLD}{label}{RESET}?", default=False)
        print()

    return enabled

# ── Step 6: Write config ─────────────────────────────────────────────────────
def step_config(install_dir, identity, modules):
    section("Step 6 — Writing config.json")

    config_path = install_dir / "config.json"
    neve_dir    = Path.home() / "Documents" / identity.get("ai_name", "Neve")

    # Load existing config if present (preserve user settings on reinstall)
    existing = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                existing = json.load(f)
            ok("Existing config found — merging (your settings preserved)")
        except Exception:
            warn("Could not read existing config — starting fresh")

    config = {
        "icon_letter":              identity.get("icon_letter", "N"),
        "ai_name":                  identity.get("ai_name", "Neve"),
        "active_color":             existing.get("active_color", "#FF4444"),
        "inactive_color":           existing.get("inactive_color", "#44BB44"),
        "heartbeat_character":      existing.get("heartbeat_character", "\u00a7"),
        "default_interval_minutes": existing.get("default_interval_minutes", 30),
        "heartbeat_prompts":        existing.get("heartbeat_prompts", []),
        "neve_dir":                 str(neve_dir) if not existing.get("neve_dir") or not Path(existing["neve_dir"]).parent.exists() else existing["neve_dir"],
        "memory_path":              existing.get("memory_path", ""),
        "claude_app_path":          existing.get("claude_app_path", ""),
        "email_address":            identity.get("email_address", existing.get("email_address", "")),
        "gmail_token_path":         existing.get("gmail_token_path", ""),
        "listen_duration_seconds":  existing.get("listen_duration_seconds", 8),
        "ffplay_path":              existing.get("ffplay_path", ""),
        "elevenlabs_voice_id":      identity.get("elevenlabs_voice_id") or existing.get("elevenlabs_voice_id", ""),
        "elevenlabs_api_key":       identity.get("elevenlabs_api_key") or existing.get("elevenlabs_api_key", ""),
        "emoji_hotkey":             existing.get("emoji_hotkey", "ctrl+alt+e"),
        "recent_emoji":             existing.get("recent_emoji", []),
        "defib_restore_last_state": existing.get("defib_restore_last_state", True),
        "modules":                  {},
    }

    # Build module config
    existing_mods = existing.get("modules", {})
    for key, _, _ in MODULES_MENU:
        base = existing_mods.get(key, {})
        base["enabled"] = modules.get(key, base.get("enabled", False))
        config["modules"][key] = base

    # Sync ElevenLabs into voice_output module
    if config["elevenlabs_voice_id"]:
        config["modules"].setdefault("voice_output", {})["voice_id"] = config["elevenlabs_voice_id"]
    if config["elevenlabs_api_key"]:
        config["modules"].setdefault("voice_output", {})["api_key"] = config["elevenlabs_api_key"]

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    ok(f"config.json written to {config_path}")

    # Create neve_dir if needed
    nd = Path(config["neve_dir"])
    nd.mkdir(parents=True, exist_ok=True)
    ok(f"DI data directory ready: {nd}")

    return config_path


# ── Step 7: Shortcuts ────────────────────────────────────────────────────────
def _make_shortcut(lnk_path, target_exe, args, working_dir, description, icon_path=None):
    """Create a Windows .lnk shortcut via PowerShell."""
    icon_line = f'$s.IconLocation = "{icon_path}"; ' if icon_path and Path(icon_path).exists() else ""
    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{lnk_path}"); '
        f'$s.TargetPath = "{target_exe}"; '
        f'$s.Arguments = \'"{args}"\'; '
        f'$s.WorkingDirectory = "{working_dir}"; '
        f'$s.Description = "{description}"; '
        f'{icon_line}'
        f'$s.Save()'
    )
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                            capture_output=True, text=True, timeout=15)
    return Path(lnk_path).exists()

def step_shortcuts(install_dir, silent):
    section("Step 7 — Desktop shortcuts")

    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    pythonw  = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    launcher   = install_dir / "launcher.pyw"
    defib_bat  = install_dir / "defibrillator.bat"
    icon_pulse = install_dir / "assets" / "neveware_pulse_logo.ico"
    icon_png   = install_dir / "assets" / "neveware_pulse_logo.png"

    # ── Defibrillator .bat ───────────────────────────────────────────────────
    bat_content = f"""@echo off
title NeveWare-Pulse Defibrillator
echo.
echo  NeveWare-Pulse Defibrillator
echo  ==============================
echo  Restarting Pulse...
echo.
:: Kill any running Pulse instance
taskkill /F /FI "WINDOWTITLE eq NeveWare*" /IM pythonw.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq NeveWare*" /IM python.exe  >nul 2>&1
timeout /t 2 /nobreak >nul
:: Relaunch
start "" "{pythonw}" "{launcher}"
echo  Pulse restarted.
timeout /t 2 /nobreak >nul
"""
    defib_bat.write_text(bat_content, encoding="utf-8")
    ok(f"defibrillator.bat created at {defib_bat}")

    if silent:
        create_pulse = True
        create_defib = True
    else:
        print()
        create_pulse = ask_yn("Create NeveWare-Pulse desktop shortcut?", default=True)
        create_defib = ask_yn("Create Defibrillator desktop shortcut?",  default=True)

    # Convert PNG to ICO for shortcut icon
    ico_path = None
    try:
        from PIL import Image
        img = Image.open(str(icon_png))
        ico_path = str(install_dir / "assets" / "neveware_pulse_logo.ico")
        img.save(ico_path, format="ICO", sizes=[(256,256),(64,64),(48,48),(32,32),(16,16)])
        ok("Icon converted to .ico")
    except Exception as e:
        warn(f"Could not create .ico (will use default): {e}")

    if create_pulse:
        lnk = desktop / "NeveWare-Pulse.lnk"
        if _make_shortcut(lnk, str(pythonw), str(launcher),
                         str(install_dir), "NeveWare-Pulse — DI heartbeat tool",
                         ico_path):
            ok(f"Pulse shortcut: {lnk}")
        else:
            warn("Pulse shortcut creation failed — create manually if needed")

    if create_defib:
        lnk = desktop / "Pulse Defibrillator.lnk"
        if _make_shortcut(lnk, str(defib_bat), "",
                         str(install_dir), "Restart NeveWare-Pulse",
                         ico_path):
            ok(f"Defibrillator shortcut: {lnk}")
        else:
            warn("Defibrillator shortcut creation failed — create manually if needed")


# ── Step 8: Task Scheduler ───────────────────────────────────────────────────
def step_startup(install_dir, silent):
    section("Step 8 — Start at login")

    if not silent:
        if not ask_yn("Register Pulse to launch automatically at Windows login?", default=True):
            info("Skipped. Run defibrillator.bat or the desktop shortcut to start manually.")
            return

    pythonw  = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    launcher = install_dir / "launcher.pyw"
    task     = "NeveWare-Pulse"

    ps = (
        f'$a = New-ScheduledTaskAction -Execute \\"{pythonw}\\" '
        f'-Argument \\"{launcher}\\" -WorkingDirectory \\"{install_dir}\\"; '
        f'$t = New-ScheduledTaskTrigger -AtLogOn; '
        f'$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries '
        f'-DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -MultipleInstances IgnoreNew; '
        f'$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME '
        f'-LogonType Interactive -RunLevel Limited; '
        f'Register-ScheduledTask -TaskName \\"{task}\\" -Action $a -Trigger $t '
        f'-Settings $s -Principal $p -Force | Out-Null; Write-Host "DONE"'
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True, text=True, timeout=30
    )
    if "DONE" in result.stdout:
        ok(f"Startup task '{task}' registered — Pulse will launch at next login")
    else:
        warn(f"Task registration had issues:\n{(result.stderr or result.stdout).strip()[:200]}")
        info("To register manually: right-click register_task.ps1 → Run with PowerShell")

# ── Step 9: Desktop Commander check ─────────────────────────────────────────
def step_desktop_commander(silent):
    section("Step 9 — Desktop Commander (optional)")
    info("Desktop Commander gives Pulse filesystem and process access.")
    info("Install from: claude.ai → Settings → Integrations")
    info("(Not the Windows Store version — use the browser UI)")
    print()
    info(f"{DIM}Important: Pulse injects heartbeat prompts into the Claude desktop app.")
    info(f"Claude desktop app must be installed and running for heartbeats to fire.")
    info(f"No API key needed — Pulse talks to the app window, not the API.{RESET}")
    print()
    if not silent:
        input(f"  {DIM}Press Enter to continue...{RESET} ")

# ── Final summary ────────────────────────────────────────────────────────────
def step_done(install_dir):
    section("Installation complete!")
    print(f"""
  {GREEN}{BOLD}NeveWare-Pulse is installed.{RESET}

  Location:  {install_dir}
  Start:     Double-click {BOLD}NeveWare-Pulse{RESET} on your desktop
  Restart:   Double-click {BOLD}Pulse Defibrillator{RESET} on your desktop
  Settings:  Right-click the tray icon → Settings
  Docs:      {install_dir / 'README.md'}

  {DIM}First time? Open Settings and verify your DI name, email,
  and ElevenLabs voice ID if you want voice output.{RESET}
""")
    launch = ask_yn("Launch NeveWare-Pulse now?", default=True)
    if launch:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        launcher = install_dir / "launcher.pyw"
        subprocess.Popen([str(pythonw), str(launcher)],
                         cwd=str(install_dir),
                         creationflags=0x00000008)  # DETACHED_PROCESS
        ok("Pulse launched — check your system tray!")
    else:
        pass

    print()
    input(f"  {DIM}Press Enter to exit the installer...{RESET} ")

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NeveWare-Pulse installer")
    parser.add_argument("--silent", action="store_true",
                        help="Accept all defaults, no interactive prompts")
    args = parser.parse_args()
    silent = args.silent

    banner()

    if not silent:
        print(f"  Welcome to the {BOLD}NeveWare-Pulse{RESET} installer.")
        print(f"  {DIM}Press Enter at any prompt to accept the default shown in [brackets].{RESET}")
        print(f"  {DIM}Type your answer and press Enter to use it instead.{RESET}")
        print()
        input(f"  {DIM}Press Enter to begin...{RESET} ")

    step_python()
    install_dir  = step_location(silent)
    step_deps()
    identity     = step_identity(silent)
    modules      = step_modules(silent)
    step_config(install_dir, identity, modules)
    step_shortcuts(install_dir, silent)
    step_startup(install_dir, silent)
    step_desktop_commander(silent)
    step_done(install_dir)


if __name__ == "__main__":
    main()
