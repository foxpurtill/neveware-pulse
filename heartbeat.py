"""
heartbeat.py — § timing loop for NeveWare-Pulse.

Alarm-clock pattern (threading.Timer, no polling, no drift).
Sends § heartbeat prompts to Claude, watches for §restart signal via file,
reads next:N value to schedule the next beat.
"""

import os
import re
import time
import random
import logging
import threading
import datetime
from pathlib import Path

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

# LOG_DIR is set from config in HeartbeatController.__init__(); default as fallback.
LOG_DIR = str(Path.home() / "Documents" / "Neve")

# How long to wait for §restart signal file (seconds)
RESPONSE_TIMEOUT = 480  # 8 minutes

# How long to poll between signal file checks (seconds)
POLL_INTERVAL = 2


def _set_log_dir(path: str):
    global LOG_DIR
    LOG_DIR = path


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _log(message: str):
    """Append a timestamped line to the heartbeat log."""
    log_file = os.path.join(LOG_DIR, "heartbeat_log.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
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


def _wait_for_restart_token(signal_path: Path, timeout: int = RESPONSE_TIMEOUT) -> tuple[bool, str]:
    """
    Watch for the DI's signal file to trigger the next beat.

    File format written by DI via Desktop Commander:
        §restart
        next:N

    On detection: reads the file, deletes it, returns (True, content).
    On timeout: returns (False, "").
    """
    deadline = time.time() + timeout

    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        if signal_path.exists():
            try:
                content = signal_path.read_text(encoding="utf-8").strip()
                signal_path.unlink()
                return True, content
            except Exception as e:
                logger.warning(f"Signal file read error: {e}")

    return False, ""


# ---------------------------------------------------------------------------
# Prompt sub-functions
# ---------------------------------------------------------------------------

def _read_prompt_plan(neve_dir: Path) -> str:
    """Read and clean the DI's prompt-plan.md. Returns body text after ---."""
    plan_path = neve_dir / "prompt-plan.md"
    if not plan_path.exists():
        return ""
    try:
        raw = plan_path.read_text(encoding="utf-8").strip()
        lines = []
        past_separator = False
        for line in raw.splitlines():
            s = line.strip()
            if s == "---":
                past_separator = True
                continue
            if not past_separator:
                continue  # skip header/comment block before ---
            if s.startswith("§restart") or s.lower().startswith("next:"):
                continue  # strip Pulse machinery tokens
            lines.append(line)
        return "\n".join(lines).strip()
    except Exception as e:
        _log(f"prompt-plan read failed: {e}")
        return ""


def _read_madlib_pool(neve_dir: Path) -> list:
    """Read all non-comment lines from madlib-pool.md."""
    madlib_path = neve_dir / "madlib-pool.md"
    if not madlib_path.exists():
        return []
    try:
        return [
            l.strip()
            for l in madlib_path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
    except Exception as e:
        _log(f"madlib-pool read failed: {e}")
        return []


def _read_voice_context(neve_dir: Path, mic_config: dict) -> str:
    """Return spoken voice context string if available, else empty string."""
    if mic_config.get("enabled", False):
        try:
            from modules.mic_listener.whisper_listener import get_spoken_context
            spoken = get_spoken_context()
            if spoken:
                _log("whisper_listener: injected spoken context into § prompt")
                return spoken
        except Exception as e:
            _log(f"whisper_listener: skipped ({e})")
    return ""


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
        self._signal_path_reminder_sent: bool = False

        # Set log dir from config at construction time
        neve_dir = Path(config.get("neve_dir", "") or Path.home() / "Documents" / "Neve")
        _set_log_dir(str(neve_dir))

    def set_module_instructions(self, instructions: str):
        """Called by tray_app when modules are loaded."""
        self._module_instructions = instructions

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
        _ensure_log_dir()
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
          [signal file reminder — once per session only]
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        heartbeat_char = self.config.get("heartbeat_character", "§")

        neve_dir = Path(self.config.get("neve_dir", "") or Path.home() / "Documents" / "Neve")

        # Read the DI's own prompt plan
        plan_text = _read_prompt_plan(neve_dir)

        # Fall back to a random default if no plan exists yet
        if not plan_text:
            user_prompts = self.config.get("heartbeat_prompts", [])
            prompt_pool = user_prompts if user_prompts else DEFAULT_HEARTBEAT_PROMPTS
            plan_text = random.choice(prompt_pool)

        # Read madlib pool and pick 3-4 random suggestions
        madlib_path = neve_dir / "madlib-pool.md"
        if not madlib_path.exists():
            self._write_default_madlib_pool(madlib_path)
        pool = _read_madlib_pool(neve_dir)
        madlib_lines = random.sample(pool, min(4, len(pool))) if pool else []

        # Assemble prompt
        prompt = f"{heartbeat_char} {timestamp}\n\n{plan_text}"

        if madlib_lines:
            prompt += "\n\n---\n" + "\n".join(f"- {l}" for l in madlib_lines)

        if self._module_instructions:
            prompt += f"\n\n{self._module_instructions}"

        # Voice/mic context
        mic_config = self.config.get("modules", {}).get("mic_listener", {})
        spoken = _read_voice_context(neve_dir, mic_config)
        if spoken:
            prompt += f"\n\n{spoken}"

        # Signal file path reminder — once per session so DI knows where to write
        if not self._signal_path_reminder_sent:
            signal_path = Path(
                self.config.get("heartbeat_signal_path", "")
                or neve_dir / "heartbeat_signal.txt"
            )
            prompt += (
                f"\n\n[Pulse signal file: to trigger the next beat, write "
                f"§restart\\nnext:N to {signal_path} via Desktop Commander]"
            )
            self._signal_path_reminder_sent = True

        return prompt

    def _fire(self):
        """Timer callback — send § prompt, wait for §restart signal, schedule next."""
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

        # Resolve signal file path
        neve_dir = Path(self.config.get("neve_dir", "") or Path.home() / "Documents" / "Neve")
        signal_path = Path(
            self.config.get("heartbeat_signal_path", "")
            or neve_dir / "heartbeat_signal.txt"
        )
        _log(f"Watching for signal file: {signal_path}")

        # Wait for §restart signal file
        found, response_text = _wait_for_restart_token(signal_path)
        if found:
            _log(f"§restart signal received.")
        else:
            _log("Warning: §restart signal not received within timeout. Assuming complete.")

        # Extract next interval
        next_interval = _parse_next_interval(response_text, fallback=self._last_interval)
        self._last_interval = next_interval

        # Log response summary (first 200 chars)
        summary = response_text[:200].replace("\n", " ").strip()
        if summary:
            _log(f"Signal content: {summary}")

        # Re-check paused state — Fox may have gone Green while we were waiting
        with self._lock:
            if self._paused or not self._running:
                _log("Heartbeat paused or stopped — skipping next schedule.")
                return

        # Schedule next beat
        self._schedule_next(delay_minutes=next_interval)
