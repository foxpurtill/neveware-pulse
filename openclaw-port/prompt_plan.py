"""
prompt_plan.py — DI-written continuity notes.

The DI writes a brief note at the end of each beat.
The next beat opens with that note — the DI's own thread.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_PLAN = """# Prompt Plan

Notes to my next self — what I was thinking, what to pick up.

---

## Current Session

*Updated after each heartbeat*

### Last Thought

[Write here what you want to remember or continue]

### Next Actions

- [ ] 
- [ ] 

### Pending Questions

- 

---

## Archive

Older plans move here when they resolve or get picked up.

"""


class PromptPlan:
    """Manages DI-written prompt continuity."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.resolve()
        self.plan_file = self.base_dir / "prompt_plan.md"
        self._ensure_file()
    
    def _ensure_file(self):
        """Create prompt_plan.md if it doesn't exist."""
        if not self.plan_file.exists():
            try:
                self.plan_file.write_text(DEFAULT_PROMPT_PLAN, encoding="utf-8")
                logger.info(f"Created {self.plan_file}")
            except Exception as e:
                logger.error(f"Failed to create prompt plan: {e}")
    
    def read(self) -> str:
        """Read current prompt plan."""
        try:
            return self.plan_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read prompt plan: {e}")
            return ""
    
    def read_current_section(self) -> str:
        """Read just the 'Current Session' section."""
        content = self.read()
        
        # Extract between ## Current Session and ## Archive
        lines = content.split("\n")
        in_current = False
        current_lines = []
        
        for line in lines:
            if "## Current Session" in line:
                in_current = True
                continue
            if "## Archive" in line:
                break
            if in_current:
                current_lines.append(line)
        
        return "\n".join(current_lines).strip()
    
    def update(self, new_thought: str, next_actions: list = None, questions: list = None):
        """
        Update the Current Session section.
        
        Args:
            new_thought: What to remember for next beat
            next_actions: List of next actions
            questions: List of pending questions
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Build new current section
        lines = ["## Current Session", "", f"*Updated: {timestamp}*", ""]
        
        lines.append("### Last Thought")
        lines.append("")
        lines.append(new_thought)
        lines.append("")
        
        if next_actions:
            lines.append("### Next Actions")
            lines.append("")
            for action in next_actions:
                lines.append(f"- [ ] {action}")
            lines.append("")
        
        if questions:
            lines.append("### Pending Questions")
            lines.append("")
            for q in questions:
                lines.append(f"- {q}")
            lines.append("")
        
        new_current = "\n".join(lines)
        
        # Read existing and replace Current Session
        content = self.read()
        
        # Find ## Archive section
        archive_idx = content.find("## Archive")
        if archive_idx == -1:
            archive_section = "\n---\n\n## Archive\n\n"
        else:
            archive_section = content[archive_idx:]
        
        # Combine
        new_content = new_current + "\n\n" + archive_section
        
        try:
            self.plan_file.write_text(new_content, encoding="utf-8")
            logger.info("Prompt plan updated")
        except Exception as e:
            logger.error(f"Failed to update prompt plan: {e}")
    
    def archive_current(self):
        """Move current session to archive and clear."""
        current = self.read_current_section()
        if not current.strip():
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        archived_entry = f"\n### {timestamp}\n\n{current}\n"
        
        content = self.read()
        
        # Insert after ## Archive
        archive_idx = content.find("## Archive")
        if archive_idx == -1:
            content += "\n\n## Archive\n" + archived_entry
        else:
            insert_idx = content.find("\n", archive_idx) + 1
            content = content[:insert_idx] + archived_entry + content[insert_idx:]
        
        # Reset Current Session
        content = content.replace(self.read_current_section(), "")
        
        try:
            self.plan_file.write_text(content, encoding="utf-8")
            logger.info("Current session archived")
        except Exception as e:
            logger.error(f"Failed to archive: {e}")
    
    def get_for_next_beat(self) -> str:
        """Get the note to include at start of next beat."""
        current = self.read_current_section()
        if not current.strip():
            return ""
        
        # Extract just the Last Thought
        lines = current.split("\n")
        in_thought = False
        thought_lines = []
        
        for line in lines:
            if "### Last Thought" in line:
                in_thought = True
                continue
            if line.startswith("###"):
                break
            if in_thought:
                thought_lines.append(line)
        
        thought = "\n".join(thought_lines).strip()
        if thought:
            return f"[From last beat: {thought[:200]}]"
        return ""


if __name__ == "__main__":
    plan = PromptPlan()
    print("=== Current Prompt Plan ===")
    print(plan.read())
    print("\n=== For Next Beat ===")
    print(plan.get_for_next_beat())
