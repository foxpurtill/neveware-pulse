"""
prompt_stamper.py — Timestamp injection on Fox's outgoing prompts.

Watches for Enter keypresses in the Claude window only.
Appends [HH:MM] to the message text before it is submitted.
Active only when tray is Red (heartbeat active / Fox away).
Suspended automatically when tray goes Green (Fox present / paused).

Implementation note:
  We intercept the Enter key globally via the `keyboard` library,
  check if the Claude window is the foreground window, and if so:
    1. Select all text in the Claude input field (Ctrl+A)
    2. Copy it (Ctrl+C)
    3. Append [HH:MM]
    4. Paste the modified text (Ctrl+V)
    5. Allow Enter to proceed (by not suppressing it further)

  The `keyboard` library intercepts at driver level — we suppress
  the initial Enter, do our modification, then re-send Enter.
"""

import time
import datetime
import logging
import threading
import keyboard
import pyperclip
import pyautogui
import win32gui

import neve_bridge

logger = logging.getLogger(__name__)

_active = False
_lock = threading.Lock()


def _current_time_stamp() -> str:
    return datetime.datetime.now().strftime("[%H:%M]")


def _is_claude_foreground() -> bool:
    """Return True if the Claude app is the currently active foreground window."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False
    title = win32gui.GetWindowText(hwnd)
    return any(p in title for p in neve_bridge.CLAUDE_TITLE_PATTERNS)


def _on_enter(event):
    """
    Global Enter key handler.
    Fires only when Claude is the foreground window.
    Appends timestamp and re-sends Enter.
    """
    if not _active:
        return

    if not _is_claude_foreground():
        return

    # Suppress this Enter
    # Read current input, append timestamp, replace, then send Enter
    try:
        # Save current clipboard
        previous = pyperclip.paste()

        # Select all in input field and copy
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.1)

        current_text = pyperclip.paste()

        # Avoid stamping an empty field or a § heartbeat prompt
        heartbeat_char = "§"
        if not current_text or current_text.strip().startswith(heartbeat_char):
            # Restore clipboard and let Enter through
            pyperclip.copy(previous)
            pyautogui.press("enter")
            return

        # Avoid double-stamping
        stamp = _current_time_stamp()
        if current_text.rstrip().endswith("]"):
            pyperclip.copy(previous)
            pyautogui.press("enter")
            return

        stamped = current_text.rstrip() + " " + stamp

        # Put stamped text back
        pyperclip.copy(stamped)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)

        # Restore original clipboard contents
        pyperclip.copy(previous)

        # Submit
        pyautogui.press("enter")

    except Exception as e:
        logger.error(f"prompt_stamper error: {e}")
        # Fail safe — send Enter anyway
        pyautogui.press("enter")


_hook_registered = False


def _register_hook():
    global _hook_registered
    if not _hook_registered:
        keyboard.on_press_key("enter", _on_enter, suppress=True)
        _hook_registered = True
        logger.info("prompt_stamper: Enter hook registered.")


def _unregister_hook():
    global _hook_registered
    if _hook_registered:
        keyboard.unhook_all()
        _hook_registered = False
        logger.info("prompt_stamper: Enter hook removed.")


def start():
    """Start the prompt stamper — registers the Enter hook. Safe to call multiple times."""
    global _active
    with _lock:
        _active = True
    _register_hook()


def stop():
    """Stop the prompt stamper entirely — unregisters the Enter hook."""
    global _active
    with _lock:
        _active = False
    _unregister_hook()


def stop_no_unhook():
    """Stop the prompt stamper without calling unhook_all.
    Used during full shutdown where _os._exit(0) handles cleanup —
    avoids killing other keyboard hooks (e.g. F10) mid-execution."""
    global _active, _hook_registered
    with _lock:
        _active = False
        _hook_registered = False
    logger.info("prompt_stamper: stopped (no unhook — process exiting).")


def pause():
    """Suspend timestamping — UNREGISTERS the hook so Enter works normally everywhere."""
    global _active
    with _lock:
        _active = False
    _unregister_hook()
    logger.info("prompt_stamper: suspended (Fox present) — Enter restored system-wide.")


def resume():
    """Resume timestamping — re-registers the hook (Fox is away / Red mode)."""
    global _active
    with _lock:
        _active = True
    _register_hook()
    logger.info("prompt_stamper: resumed (Fox away).")
