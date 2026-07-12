"""
utils.py — Shared utilities for NeveWare-Pulse-OpenClaw.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any


def setup_logging(name: str = "pulse", log_dir: Path = None) -> logging.Logger:
    """Set up logging with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console.setFormatter(console_format)
    logger.addHandler(console)
    
    # File handler (if log_dir provided)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "pulse.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def format_timestamp(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def parse_timestamp(ts_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse string to datetime."""
    try:
        return datetime.strptime(ts_str, format_str)
    except ValueError:
        return None


def estimate_tokens(text: str) -> int:
    """Rough token estimate (2 chars ≈ 1 token)."""
    return len(text) // 2


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximate token limit."""
    max_chars = max_tokens * 2
    if len(text) <= max_chars:
        return text
    return text[:max_chars-3] + "..."


def load_json_safe(path: Path, default: Any = None) -> Any:
    """Safely load JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        logging.getLogger(__name__).warning(f"Failed to load {path}: {e}")
        return default


def save_json_safe(path: Path, data: Any) -> bool:
    """Safely save JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to save {path}: {e}")
        return False


class StateManager:
    """Simple state persistence."""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._cache = {}
        self._load()
    
    def _load(self):
        """Load state from file."""
        self._cache = load_json_safe(self.state_file, {})
    
    def _save(self):
        """Save state to file."""
        save_json_safe(self.state_file, self._cache)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self._cache.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set state value and save."""
        self._cache[key] = value
        self._save()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple values."""
        self._cache.update(updates)
        self._save()


def get_kira_memory_path() -> Path:
    """Get path to Kira's memory directory."""
    # Try common locations
    paths = [
        Path.home() / "Documents" / "Kira",
        Path.home() / "Documents" / "kira",
        Path.home() / "kira",
    ]
    for p in paths:
        if p.exists():
            return p
    # Default to first option
    return paths[0]


def get_openclaw_workspace() -> Optional[Path]:
    """Try to find OpenClaw workspace."""
    # From environment or common paths
    env_path = os.environ.get("OPENCLAW_WORKSPACE")
    if env_path:
        return Path(env_path)
    
    paths = [
        Path.home() / "AppData" / "Roaming" / "openclaw" / "workspace",
        Path.home() / ".openclaw" / "workspace",
    ]
    for p in paths:
        if p.exists():
            return p
    return None


if __name__ == "__main__":
    # Test
    logger = setup_logging("test")
    logger.info("Logging test")
    
    print(f"Timestamp: {format_timestamp()}")
    print(f"Tokens in 'hello world': {estimate_tokens('hello world')}")
    
    test_path = Path(".test_state.json")
    state = StateManager(test_path)
    state.set("test", "value")
    print(f"State: {state.get('test')}")
    test_path.unlink(missing_ok=True)
