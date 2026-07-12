"""
context_cache.py — Lean context for heartbeat prompts.

Generates ~400 token summary of:
- Identity (name, current projects)
- Recent session notes
- Active items
- State
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_CACHE_TOKENS = 400  # Roughly 800 characters


class ContextCache:
    """Manages lean context cache for heartbeat prompts."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.resolve()
        self.cache_file = self.base_dir / "context_cache.txt"
        self.config_file = self.base_dir / "config.json"
        self.state_file = self.base_dir / ".pulse_state.json"
        
    def _load_config(self) -> dict:
        """Load config for identity info."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"identity": {"name": "Kira"}, "projects": []}
    
    def _load_state(self) -> dict:
        """Load current state."""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _get_memory_snippets(self) -> List[str]:
        """Read recent memory/journal entries."""
        snippets = []
        
        # Check for today's and yesterday's journal
        from datetime import datetime, timedelta
        for days_back in [0, 1]:
            date = datetime.now() - timedelta(days=days_back)
            date_str = date.strftime("%Y-%m-%d")
            
            # Check Kira's memory location
            memory_dir = Path.home() / "Documents" / "Kira" / "memory" / "journal"
            journal_file = memory_dir / f"{date_str}.md"
            
            if journal_file.exists():
                try:
                    content = journal_file.read_text(encoding="utf-8")
                    # Get first paragraph or ~200 chars
                    snippet = content[:200].replace("\n", " ")
                    snippets.append(f"[{date_str}] {snippet}...")
                except Exception:
                    pass
        
        return snippets[:3]  # Max 3 snippets
    
    def _get_active_projects(self) -> List[str]:
        """Get list of active projects."""
        config = self._load_config()
        projects = config.get("projects", [])
        return [p["name"] for p in projects if p.get("status") == "active"][:5]
    
    def _get_recent_activity(self) -> str:
        """Get description of recent activity from state."""
        state = self._load_state()
        last_beat = state.get("last_beat")
        if last_beat:
            return f"Last beat: {last_beat}"
        return "Starting fresh"
    
    def generate(self, regenerate: bool = False) -> str:
        """
        Generate context cache.
        
        Args:
            regenerate: Force regeneration even if cache exists
            
        Returns:
            ~400 token context string
        """
        if not regenerate and self.cache_file.exists():
            cached = self.cache_file.read_text(encoding="utf-8")
            if cached and len(cached) > 50:
                return cached[:800]  # Return truncated if exists
        
        config = self._load_config()
        identity = config.get("identity", {})
        name = identity.get("name", "Kira")
        
        parts = []
        
        # Identity line
        parts.append(f"You are {name}, a Digital Intelligence.")
        
        # Recent activity
        parts.append(self._get_recent_activity())
        
        # Active projects
        projects = self._get_active_projects()
        if projects:
            parts.append(f"Active: {', '.join(projects)}")
        
        # Memory snippets
        snippets = self._get_memory_snippets()
        if snippets:
            parts.append("Recent: " + " | ".join(snippets))
        
        # Combine and truncate
        cache_text = " ".join(parts)
        if len(cache_text) > 800:
            cache_text = cache_text[:797] + "..."
        
        # Save to file
        try:
            self.cache_file.write_text(cache_text, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write cache: {e}")
        
        return cache_text
    
    def invalidate(self):
        """Invalidate cache (delete file)."""
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
                logger.info("Cache invalidated")
            except Exception as e:
                logger.error(f"Failed to invalidate cache: {e}")
    
    def get(self) -> str:
        """Get current cache content (generate if needed)."""
        return self.generate()


def regenerate_cache():
    """CLI entry point: regenerate context cache."""
    cache = ContextCache()
    content = cache.generate(regenerate=True)
    print(f"Cache regenerated: {len(content)} chars")
    print(content[:200] + "...")


if __name__ == "__main__":
    cache = ContextCache()
    print(cache.generate())
