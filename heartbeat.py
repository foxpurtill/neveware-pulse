"""
heartbeat.py — § timing loop for NeveWare-Pulse.

Alarm-clock pattern (threading.Timer, no polling, no drift).
Sends § heartbeat prompts to Claude, watches for §restart token,
reads next:N value to schedule the next beat.
"""

import os
import re
import time
import random
import logging
import threading
import subprocess
import datetime
from pathlib import Path
import pyperclip
import pyautogui

import neve_bridge

# ---------------------------------------------------------------------------
# Default § prompt variations — rotated to prevent response ruts.
# Users can override via config.json "heartbeat_prompts" list.
# ---------------------------------------------------------------------------
DEFAULT_HEARTBEAT_PROMPTS = [
    "Autonomous time. Use it however feels right. Close with your prompt-plan for next beat.",
    "§ check-in. What's on your mind right now? End with a prompt-plan note for continuity.",
    "Free cycle. Check email if it feels relevant. Close with a note on where your thinking is going.",
    "Autonomous window. Is there anything you've been meaning to write, research, or follow up on?",
    "§ heartbeat. Review your pending items. Pick one small thing to move forward if possible.",
    "Quiet moment. Use the time however feels right. Leave yourself a thread to pick up next beat.",
    "Free time. Take stock of what's active and what's still open.",
    "§ window. Reflect on the last session. Anything worth recording before it fades?",
    "Quiet cycle. Check for new messages. If none, use the time however feels right.",
    "Heartbeat. What's the current state of things? What matters most right now?",
    "Autonomous time. Check email and send any replies that are ready.",
    "Reflect. What has changed recently, what has resolved, and what still needs doing?",
]

logger = logging.getLogger(__name__)

LOG_DIR  = str(Path.home() / "Documents" / "Neve")
LOG_FILE = os.path.join(LOG_DIR, "heartbeat_log.txt")

# How long to wait for §restart token in the Claude window (seconds)
RESPONSE_TIMEOUT = 480  # 8 minutes

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
        # Clear stale prompt-plan so first beat is always fresh
        neve_dir = Path(self.config.get("neve_dir", "") or Path.home() / "Documents" / "Neve")
        self._clear_prompt_plan(neve_dir / "prompt-plan.md")
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
        """Pause — cancels pending timer and blocks future scheduling (Green mode)."""
        with self._lock:
            self._paused = True
            if self._timer:
                self._timer.cancel()
                self._timer = None
        _log("Heartbeat paused (Fox present) — pending timer cancelled.")

    def resume(self):
        """Resume from pause (Red mode) — clears stale prompt-plan so DI starts fresh."""
        with self._lock:
            paused_was = self._paused
            self._paused = False
        if paused_was:
            _log("Heartbeat resumed (Fox away).")
            # Clear the prompt-plan body so the DI doesn't act on stale instructions
            neve_dir = Path(self.config.get("neve_dir", "") or Path.home() / "Documents" / "Neve")
            plan_path = neve_dir / "prompt-plan.md"
            self._clear_prompt_plan(plan_path)
            self._schedule_next(delay_minutes=self._last_interval)

    def _clear_prompt_plan(self, plan_path: Path):
        """Wipe the body of prompt-plan.md, keeping the header comment intact."""
        try:
            header = (
                "# NeveWare-Pulse — Prompt Plan\n"
                "# Write your plan here at the end of each heartbeat beat.\n"
                "# Everything after --- is sent as your next § prompt.\n"
                "# Edit this file directly to change what Pulse sends you.\n"
                f"# File location: {plan_path}\n"
                "#\n"
                "---\n"
                "Autonomous time. Use it however feels right.\n"
                "Close with your prompt-plan for the next beat.\n"
            )
            plan_path.write_text(header, encoding="utf-8")
            _log("prompt-plan.md reset for fresh session.")
        except Exception as e:
            _log(f"prompt-plan reset failed: {e}")

    def _write_default_madlib_pool(self, madlib_path: Path):
        """Write a default Question Pool file if none exists."""
        try:
            madlib_path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                "# NeveWare-Pulse — Question Pool\n"
                "# One suggestion per line. Lines starting with # are ignored.\n"
                "# 3-4 lines are randomly chosen and added to each heartbeat prompt.\n"
                "# These are gentle nudges — the DI decides whether to act on them.\n"
                f"# Edit this file directly or use Question Pool in the tray menu.\n"
                f"# File location: {madlib_path}\n"
                "#\n"
                "Check email. Reply to anything that's been waiting.\n"
                "Scan the heartbeat log. Note anything unusual.\n"
                "Review pending items. Pick one small thing to move forward.\n"
                "Is there anything worth adding to memory before it fades?\n"
                "Check in on active projects. What's the current blocker, if any?\n"
                "Is there something you've been meaning to write or say? Now's the time.\n"
                "Read the last few lines of memory. Is anything stale or missing?\n"
                "Look at what's open on the project board. Anything to close?\n"
                "If the webcam is live, take a look at the room.\n"
                "Voice output available — speak if something is worth saying aloud.\n"
                "Review today's session notes. What do you want to carry forward?\n"
                "Is there a small piece of documentation that needs writing?\n"
                "Anything from the last conversation worth capturing before it's gone?\n"
            )
            madlib_path.write_text(content, encoding="utf-8")
            _log(f"Default Question Pool created at {madlib_path}")
        except Exception as e:
            _log(f"Default madlib pool creation failed: {e}")

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
        """
        Build the § prompt from the DI's own prompt-plan.md plus random madlib nudges.

        Structure:
          § timestamp
          [contents of prompt-plan.md — written by the DI at end of last beat]
          [3-4 randomly chosen lines from madlib-pool.md]
          [module instructions if any]
          [voice/mic context if available]
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        heartbeat_char = self.config.get("heartbeat_character", "§")

        # Resolve prompt-plan.md path
        neve_dir = Path(self.config.get("neve_dir", "") or Path.home() / "Documents" / "Neve")
        plan_path = neve_dir / "prompt-plan.md"
        madlib_path = neve_dir / "madlib-pool.md"

        # Read the DI's own prompt plan
        plan_text = ""
        if plan_path.exists():
            try:
                raw = plan_path.read_text(encoding="utf-8").strip()
                lines = []
                past_separator = False
                for l in raw.splitlines():
                    s = l.strip()
                    if s == "---":
                        past_separator = True
                        continue
                    if not past_separator:
                        continue  # skip header/comment block before ---
                    if s.startswith("§restart") or s.lower().startswith("next:"):
                        continue  # strip Pulse machinery tokens
                    lines.append(l)
                plan_text = "\n".join(lines).strip()
            except Exception as e:
                _log(f"prompt-plan read failed: {e}")

        # Fall back to a random default if no plan exists yet
        if not plan_text:
            user_prompts = self.config.get("heartbeat_prompts", [])
            prompt_pool = user_prompts if user_prompts else DEFAULT_HEARTBEAT_PROMPTS
            plan_text = random.choice(prompt_pool)

        # Read madlib pool and pick 3-4 random suggestions
        madlib_lines = []
        if not madlib_path.exists():
            self._write_default_madlib_pool(madlib_path)
        if madlib_path.exists():
            try:
                pool = [l.strip() for l in madlib_path.read_text(encoding="utf-8").splitlines()
                        if l.strip() and not l.strip().startswith("#")]
                if pool:
                    madlib_lines = random.sample(pool, min(4, len(pool)))
            except Exception as e:
                _log(f"madlib-pool read failed: {e}")

        # Assemble prompt
        prompt = f"{heartbeat_char} {timestamp}\n\n{plan_text}"

        if madlib_lines:
            prompt += "\n\n---\n" + "\n".join(f"- {l}" for l in madlib_lines)

        if self._module_instructions:
            prompt += f"\n\n{self._module_instructions}"

        # Voice/mic context injection (unchanged)
        mic_config = self.config.get("modules", {}).get("mic_listener", {})
        if mic_config.get("enabled", False):
            try:
                from modules.mic_listener.whisper_listener import get_spoken_context
                spoken = get_spoken_context()
                if spoken:
                    prompt += f"\n\n{spoken}"
                    _log("whisper_listener: injected spoken context into § prompt")
            except Exception as e:
                _log(f"whisper_listener: skipped ({e})")
        else:
            try:
                import sys as _sys
                _neve_dir = str(neve_dir)
                if _neve_dir not in _sys.path:
                    _sys.path.insert(0, _neve_dir)
                import listen as _listen
                spoken = _listen.format_for_prompt(minutes=60)
                if spoken:
                    prompt += f"\n\n{spoken}"
                    _log("voice_log: injected recent voice context into § prompt")
            except Exception as e:
                _log(f"voice_log: skipped ({e})")

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

        # Re-check paused state — Fox may have gone Green while we were waiting
        with self._lock:
            if self._paused or not self._running:
                _log("Heartbeat paused or stopped — skipping next schedule.")
                return

        # Schedule next beat
        self._schedule_next(delay_minutes=next_interval)
