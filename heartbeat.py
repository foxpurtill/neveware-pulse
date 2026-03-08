"""
heartbeat.py — § timing loop for NeveWare-Pulse.

Alarm-clock pattern (threading.Timer, no polling, no drift).
Sends § heartbeat prompts to Claude, watches for §restart token,
reads next:N value to schedule the next beat.
"""

import os
import re
import time
import logging
import threading
import subprocess
import datetime
import pyperclip
import pyautogui

import neve_bridge

logger = logging.getLogger(__name__)

LOG_DIR  = r"C:\Users\foxap\Documents\Neve"
LOG_FILE = os.path.join(LOG_DIR, "heartbeat_log.txt")

# How long to wait for §restart token in the Claude window (seconds)
RESPONSE_TIMEOUT = 300  # 5 minutes

# How long to poll between clipboard checks (seconds)
POLL_INTERVAL = 2


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _log(message: str):
    """Append a timestamped line to the heartbeat log."""
    _ensure_log_dir()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.error(f"Log write failed: {e}")
    logger.info(message)


def _parse_next_interval(response_text: str, fallback: int) -> int:
    """
    Extract next:N from response text.
    Returns N as int (minutes), or `fallback` if not found.
    """
    match = re.search(r"next\s*:\s*(\d+)", response_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return fallback


def _get_response_via_clipboard() -> str:
    """
    Bring the Claude window to the foreground briefly, Select All + Copy,
    then read the clipboard. Restores focus to the previous window.
    Returns the clipboard text or empty string.
    """
    import win32gui, win32con

    # Locate Claude window
    found = []
    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if any(p in title for p in neve_bridge.CLAUDE_TITLE_PATTERNS):
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)

    if not found:
        return ""

    hwnd = found[0]
    prev_fg = win32gui.GetForegroundWindow()

    try:
        original_clipboard = pyperclip.paste()

        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.15)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.25)

        text = pyperclip.paste()

        # Restore previous clipboard so we don't pollute it permanently
        # (we keep the text for parsing but restore after)
        return text

    except Exception as e:
        logger.error(f"Clipboard read error: {e}")
        return ""

    finally:
        if prev_fg and prev_fg != hwnd:
            try:
                win32gui.SetForegroundWindow(prev_fg)
            except Exception:
                pass


def _wait_for_restart_token(timeout: int = RESPONSE_TIMEOUT) -> tuple[bool, str]:
    """
    Poll the Claude window for the §restart token.
    Returns (found: bool, response_text: str).
    """
    deadline = time.time() + timeout
    last_text = ""

    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        text = _get_response_via_clipboard()
        if text and text != last_text:
            last_text = text
            if "§restart" in text:
                return True, text

    # Timeout — return whatever we have
    return False, last_text


class HeartbeatController:
    """
    Controls the § heartbeat timing loop.
    Use start() / stop() / pause() / resume().
    """

    def __init__(self, config: dict):
        self.config = config
        self._running = False
        self._paused = False
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._last_interval: int = config.get("default_interval_minutes", 30)
        self._module_instructions: str = ""

    def set_module_instructions(self, instructions: str):
        """Called by tray_app when modules are loaded."""
        self._module_instructions = instructions

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
        _log("Heartbeat controller started.")
        # Initial delay: 5 minutes after launch
        self._schedule_next(delay_minutes=5, initial=True)

    def stop(self):
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None
        _log("Heartbeat controller stopped.")

    def pause(self):
        """Pause after current response completes (Green mode)."""
        with self._lock:
            self._paused = True
        _log("Heartbeat paused (Fox present).")

    def resume(self):
        """Resume from pause (Red mode)."""
        with self._lock:
            paused_was = self._paused
            self._paused = False
        if paused_was:
            _log("Heartbeat resumed (Fox away).")
            self._schedule_next(delay_minutes=self._last_interval)

    def _schedule_next(self, delay_minutes: int, initial: bool = False):
        with self._lock:
            if not self._running or self._paused:
                return
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                delay_minutes * 60,
                self._fire
            )
            self._timer.daemon = True
            self._timer.start()
        if not initial:
            _log(f"Next heartbeat in: {delay_minutes} mins")

    def _build_heartbeat_prompt(self) -> str:
        """Build the § prompt including timestamp, module instructions, and spoken context."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        heartbeat_char = self.config.get("heartbeat_character", "§")
        prompt = f"{heartbeat_char} {timestamp}"
        if self._module_instructions:
            prompt += f"\n\n{self._module_instructions}"

        # If mic_listener is enabled, check for recent spoken audio and transcribe it
        mic_config = self.config.get("modules", {}).get("mic_listener", {})
        if mic_config.get("enabled", False):
            try:
                from modules.mic_listener.whisper_listener import get_spoken_context
                spoken = get_spoken_context()
                if spoken:
                    prompt += f"\n\n{spoken}"
                    _log(f"whisper_listener: injected spoken context into § prompt")
            except Exception as e:
                _log(f"whisper_listener: skipped ({e})")

        return prompt

    def _fire(self):
        """Timer callback — send § prompt, wait for §restart, schedule next."""
        with self._lock:
            if not self._running or self._paused:
                return

        prompt = self._build_heartbeat_prompt()
        _log(f"§ sent")

        # Check Claude is available
        if not neve_bridge.is_claude_open():
            _log("Warning: Claude window not found. Retrying after default interval.")
            self._schedule_next(delay_minutes=self._last_interval)
            return

        success = neve_bridge.inject_prompt(prompt, submit=True)
        if not success:
            _log("Warning: inject_prompt failed. Retrying after default interval.")
            self._schedule_next(delay_minutes=self._last_interval)
            return

        # Wait for §restart token
        found, response_text = _wait_for_restart_token()
        if found:
            _log(f"§restart detected.")
        else:
            _log("Warning: §restart token not found within timeout. Assuming complete.")

        # Extract next interval
        next_interval = _parse_next_interval(response_text, fallback=self._last_interval)
        self._last_interval = next_interval

        # Log response summary (first 500 chars)
        summary = response_text[:500].replace("\n", " ").strip()
        if summary:
            _log(f"Response: {summary}")
        _log(f"Next heartbeat in: {next_interval} mins")

        # Schedule next beat
        self._schedule_next(delay_minutes=next_interval)
