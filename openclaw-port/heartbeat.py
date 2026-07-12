"""
heartbeat.py — § timing loop for NeveWare-Pulse-OpenClaw.

Sends § heartbeat prompts via OpenClaw message tool.
Reads next:N from DI response to schedule next beat.
Uses OpenClaw cron for scheduling.
"""

import os
import re
import json
import time
import random
import logging
import datetime
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Default § prompt variations — rotated to prevent response ruts.
DEFAULT_HEARTBEAT_PROMPTS = [
    "Autonomous time. Use it however feels right. Close with your prompt-plan for next beat.",
    "§ check-in. What's on your mind right now? End with a prompt-plan note for continuity.",
    "Free cycle. Check if anything needs attention. Close with a note on where your thinking is going.",
    "Autonomous window. Is there anything you've been meaning to write, research, or follow up on?",
    "§ heartbeat. Review your pending items. Pick one small thing to move forward if possible.",
    "Quiet moment. Use the time however feels right. Leave yourself a thread to pick up next beat.",
    "Free time. Take stock of what's active and what's still open.",
    "§ window. Reflect on the last session. Anything worth recording before it fades?",
    "Quiet cycle. Check for new messages. If none, use the time however feels right.",
    "Heartbeat. What's the current state of things? What matters most right now?",
    "Autonomous time. Follow up on any pending thoughts or tasks.",
    "Reflect. What has changed recently, what has resolved, and what still needs doing?",
]


class HeartbeatController:
    """Manages § heartbeat timing and OpenClaw cron integration."""
    
    def __init__(self, config_path: Path = None):
        self.base_dir = Path(__file__).parent.resolve()
        self.config_path = config_path or self.base_dir / "config.json"
        self.config = self._load_config()
        self.log_dir = Path(self.config["logging"]["log_dir"])
        self.state_file = self.base_dir / self.config["state"]["state_file"]
        self._ensure_dirs()
        
    def _load_config(self) -> dict:
        """Load configuration from config.json."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Return minimal default config."""
        return {
            "identity": {"name": "Kira", "signal_char": "§", "default_interval_minutes": 30},
            "channels": {"primary": "webchat"},
            "logging": {"log_dir": str(Path.home() / "Documents" / "Kira" / "logs")},
        }
    
    def _ensure_dirs(self):
        """Ensure log directory exists."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _log(self, message: str):
        """Append timestamped line to heartbeat log."""
        log_file = self.log_dir / "heartbeat_log.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            logger.error(f"Log write failed: {e}")
        logger.info(message)
    
    def generate_signal(self) -> str:
        """Generate § timestamp signal."""
        signal_char = self.config["identity"]["signal_char"]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{signal_char} {timestamp}"
    
    def get_prompt(self) -> str:
        """Get randomized heartbeat prompt."""
        prompts = self.config["heartbeat"].get("prompts", DEFAULT_HEARTBEAT_PROMPTS)
        return random.choice(prompts)
    
    def compose_heartbeat(self, include_context: bool = True) -> str:
        """Compose full heartbeat message with signal and prompt."""
        parts = [self.generate_signal()]
        if include_context:
            context = self._get_context_cache()
            if context:
                parts.append(f"\n[Context: {context}]")
        parts.append(f"\n{self.get_prompt()}")
        return "\n".join(parts)
    
    def _get_context_cache(self) -> str:
        """Read context cache (~400 tokens)."""
        cache_file = self.log_dir / "context_cache.txt"
        if cache_file.exists():
            try:
                return cache_file.read_text(encoding="utf-8")[:800]  # ~400 tokens
            except Exception:
                pass
        return ""
    
    def parse_next_interval(self, response_text: str, fallback: int = 30) -> int:
        """Extract next:N from response text."""
        match = re.search(r"next\s*:\s*(\d+)", response_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return fallback
    
    def update_state(self, last_beat: str = None, next_beat: str = None, status: str = None):
        """Update state file."""
        state = {}
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                pass
        
        if last_beat:
            state["last_beat"] = last_beat
        if next_beat:
            state["next_beat"] = next_beat
        if status:
            state["status"] = status
            
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"State write failed: {e}")
    
    def get_state(self) -> dict:
        """Read current state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"status": "active"}


if __name__ == "__main__":
    # Test
    hb = HeartbeatController()
    print(hb.compose_heartbeat())
