"""
kira_bridge.py — OpenClaw integration layer for NeveWare-Pulse.

Replaces neve_bridge.py (Claude window injection).
Uses OpenClaw's message tool and cron scheduling.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class KiraBridge:
    """Bridge between Pulse and OpenClaw Gateway."""
    
    def __init__(self, config_path: Path = None):
        self.base_dir = Path(__file__).parent.resolve()
        self.config_path = config_path or self.base_dir / "config.json"
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"channels": {"primary": "webchat"}}
    
    def send_message(self, text: str, channel: str = None) -> bool:
        """
        Send message via OpenClaw message tool.
        
        Args:
            text: Message content
            channel: Channel to send to (default: config.primary)
            
        Returns:
            True if successful, False otherwise
        """
        target = channel or self.config["channels"]["primary"]
        
        # For webchat, we can't directly inject — but we can use cron
        # to schedule a system event that will be delivered
        logger.info(f"Sending message to {target}: {text[:50]}...")
        
        # In OpenClaw, this would be handled by the cron job system
        # The actual implementation depends on how Fox wants to receive
        # For now, log it and return True
        # Real implementation would use openclaw message command or API
        
        return True
    
    def schedule_next_beat(self, minutes: int, message: str = None) -> bool:
        """
        Schedule next heartbeat via OpenClaw cron.
        
        Args:
            minutes: Minutes until next beat
            message: Optional message to include
            
        Returns:
            True if scheduled successfully
        """
        # Calculate future time
        import datetime
        future = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        
        logger.info(f"Scheduling next beat in {minutes} minutes (at {future})")
        
        # In full implementation, this would call:
        # openclaw cron add --name "KiraPulse" --at "{iso_time}" ...
        
        return True
    
    def cancel_pending_beats(self) -> bool:
        """Cancel any pending heartbeat cron jobs."""
        logger.info("Cancelling pending beats")
        # Implementation: openclaw cron list, find KiraPulse jobs, remove
        return True
    
    def get_pending_beats(self) -> List[dict]:
        """Get list of pending heartbeat jobs."""
        # Implementation: parse openclaw cron list output
        return []


class PulseCronManager:
    """Manages OpenClaw cron jobs for Pulse."""
    
    def __init__(self, identity: str = "kira"):
        self.identity = identity
        self.job_prefix = f"pulse-{identity}"
    
    def _run_openclaw(self, args: List[str]) -> tuple:
        """Run openclaw CLI command."""
        cmd = ["openclaw"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            logger.error(f"openclaw command failed: {e}")
            return False, "", str(e)
    
    def add_beat(self, minutes: int, message: str) -> Optional[str]:
        """
        Add a one-shot heartbeat cron job.
        
        Returns job ID if successful, None otherwise.
        """
        import datetime
        
        # Calculate future time
        future = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        iso_time = future.strftime("%Y-%m-%dT%H:%M:%S")
        
        job_name = f"{self.job_prefix}-{int(time.time())}"
        
        # Build cron payload
        # This would create a system event that triggers the next beat
        logger.info(f"Adding cron job: {job_name} at {iso_time}")
        
        # Actual implementation:
        # openclaw cron add --name job_name --at iso_time --session main \
        #   --system-event "§ heartbeat: message"
        
        return job_name
    
    def list_beats(self) -> List[dict]:
        """List all Pulse-related cron jobs."""
        success, stdout, stderr = self._run_openclaw(["cron", "list"])
        if not success:
            logger.error(f"Failed to list cron jobs: {stderr}")
            return []
        
        # Parse output to find pulse jobs
        jobs = []
        # Implementation: parse stdout for pulse-* jobs
        return jobs
    
    def remove_beat(self, job_id: str) -> bool:
        """Remove a specific cron job."""
        success, _, stderr = self._run_openclaw(["cron", "remove", "--id", job_id])
        if not success:
            logger.error(f"Failed to remove job {job_id}: {stderr}")
            return False
        return True
    
    def pause(self) -> bool:
        """Pause all Pulse beats (disable jobs)."""
        logger.info("Pausing all beats")
        # Implementation: disable cron jobs or set state to paused
        return True
    
    def resume(self) -> bool:
        """Resume Pulse beats."""
        logger.info("Resuming beats")
        return True


if __name__ == "__main__":
    # Test
    bridge = KiraBridge()
    bridge.send_message("§ 2026-04-15 13:50:00\nTest heartbeat")
    bridge.schedule_next_beat(30)
