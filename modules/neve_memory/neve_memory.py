"""
neve_memory.py — Memory backup module for NeveWare-Pulse.

Reads and writes the DI's memory.json (path configured in module settings).
Auto-backs up to GitHub (configured repo).

This module is identity-neutral — configure your own paths in Settings.
The pattern is reusable — this is the reference implementation.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

_config: dict = {}

_DEFAULT_MEMORY_PATH = str(Path.home() / "Documents" / "Neve" / "memory.json")


def on_enable(module_config: dict):
    global _config
    _config = module_config
    memory_path = module_config.get("memory_path", "") or _DEFAULT_MEMORY_PATH
    logger.info(f"neve_memory: enabled. Memory path: {memory_path}")

    memory_dir = Path(memory_path).parent
    memory_dir.mkdir(parents=True, exist_ok=True)

    if not Path(memory_path).exists():
        initial_memory = {
            "created": datetime.now().isoformat(),
            "notes": [],
            "last_updated": None
        }
        try:
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(initial_memory, f, indent=2)
            logger.info(f"neve_memory: created empty memory.json at {memory_path}")
        except Exception as e:
            logger.error(f"neve_memory: failed to create memory.json: {e}")


def on_disable():
    logger.info("neve_memory: disabled.")


def read_memory() -> dict:
    """Read current memory.json contents."""
    memory_path = _config.get("memory_path", "") or _DEFAULT_MEMORY_PATH
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"neve_memory read_memory: {e}")
        return {}


def write_memory(data: dict) -> bool:
    """Write updated memory data to memory.json."""
    memory_path = _config.get("memory_path", "") or _DEFAULT_MEMORY_PATH
    try:
        data["last_updated"] = datetime.now().isoformat()
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"neve_memory: memory.json updated.")
        return True
    except Exception as e:
        logger.error(f"neve_memory write_memory: {e}")
        return False


def backup_to_github() -> bool:
    """
    Commit and push memory.json to the configured GitHub repository.
    Requires git to be available and the repo to be cloned/accessible.
    Uses gh CLI if available, otherwise plain git.
    """
    if not _config.get("auto_backup", True):
        return True

    memory_path = _config.get("memory_path", r"C:\Users\foxap\Documents\Neve\memory.json")
    memory_dir = Path(memory_path).parent

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if directory is a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(memory_dir), capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.warning("neve_memory: memory directory is not a git repo. Skipping backup.")
            return False

        subprocess.run(["git", "add", str(memory_path)], cwd=str(memory_dir), check=True)
        subprocess.run(
            ["git", "commit", "-m", f"memory update: {timestamp}"],
            cwd=str(memory_dir), capture_output=True
        )
        subprocess.run(["git", "push"], cwd=str(memory_dir), capture_output=True, check=True)
        logger.info("neve_memory: backup to GitHub complete.")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"neve_memory backup_to_github: {e}")
        return False
    except Exception as e:
        logger.error(f"neve_memory backup_to_github unexpected: {e}")
        return False
