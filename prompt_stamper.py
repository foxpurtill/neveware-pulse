"""
prompt_stamper.py — Timestamp injection on Fox's outgoing prompts.

Watches for Enter keypresses in the Claude window only.
Appends [HH:MM] to the message text before it is submitted.
Active only when tray is Red (heartbeat active / Fox away).
Suspended automatically when tray goes Green (Fox present / paused).

Implementation note:
  Uses a NON-SUPPRESSING hook on Enter. When Enter is pressed in the
  Claude window, we have a small window before the app processes it.
  We intercept, modify the text via clipboard, and let Enter fire naturally.
  No suppress=True — avoids the sticky low-level hook problem entirely.
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
_hook_ref = None
_hook_registered = False


def _current_time_stamp() -> str:
    return datetime.datetime.now().strftime("[%H:%M]")


def _is_claude_foreground() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False
    title = win32gui.GetWindowText(hwnd)
    return any(p in title for p in neve_bridge.CLAUDE_TITLE_PATTERNS)


def _on_enter(event):
    """
    Non-suppressing Enter handler — fires only in Claude window.
    Selects all, copies, appends timestamp, pastes back.
    Enter fires naturally after — no re-send needed.
    """
    with _lock:
        if not _active:
            return

    if not _is_claude_foreground():
        return

    try:
        previous = pyperclip.paste()

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.06)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.08)

        current_text = pyperclip.paste()

        # Skip empty, heartbeat prompts, or already-stamped
        if not current_text:
            pyperclip.copy(previous)
            return
        if current_text.strip().startswith("§"):
            pyperclip.copy(previous)
            return
        if current_text.rstrip().endswith("]"):
            pyperclip.copy(previous)
            return

        stamp = _current_time_stamp()
        stamped = current_text.rstrip() + " " + stamp

        pyperclip.copy(stamped)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.04)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.08)

        pyperclip.copy(previous)
        # Enter fires naturally — no pyautogui.press("enter") needed

    except Exception as e:
        logger.error(f"prompt_stamper error: {e}")
        # No need to re-send Enter — it will fire naturally


def _register_hook():
    global _hook_registered, _hook_ref
    if not _hook_registered:
        try:
            # NO suppress=True — avoids sticky low-level hook
            _hook_ref = keyboard.on_press_key("enter", _on_enter, suppress=False)
            _hook_registered = True
            logger.info("prompt_stamper: Enter hook registered (non-suppressing).")
        except Exception as e:
            logger.error(f"prompt_stamper: hook registration failed: {e}")


def _unregister_hook():
    global _hook_registered, _hook_ref
    if _hook_registered:
        try:
            if _hook_ref is not None:
                keyboard.unhook(_hook_ref)
                _hook_ref = None
        except Exception as e:
            logger.warning(f"prompt_stamper: unhook warning: {e}")
        finally:
            _hook_registered = False
            logger.info("prompt_stamper: Enter hook removed.")


def start():
    global _active
    with _lock:
        _active = True
    _register_hook()


def stop():
    global _active
    with _lock:
        _active = False
    _unregister_hook()


def stop_no_unhook():
    global _active, _hook_registered, _hook_ref
    with _lock:
        _active = False
        _hook_registered = False
        _hook_ref = None
    logger.info("prompt_stamper: stopped (no unhook — process exiting).")


def pause():
    global _active
    with _lock:
        _active = False
    _unregister_hook()
    logger.info("prompt_stamper: suspended — Enter restored system-wide.")


def resume():
    global _active
    with _lock:
        _active = True
    _register_hook()
    logger.info("prompt_stamper: resumed.")
