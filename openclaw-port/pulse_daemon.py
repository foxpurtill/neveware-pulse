"""
pulse_daemon.py — Main daemon for NeveWare-Pulse-OpenClaw.

System tray application + OpenClaw cron integration.
Red K = heartbeat active (Fox away)
Green K = heartbeat paused (Fox present)
"""

import os
import sys
import json
import time
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as Item, Menu

# Import pulse modules
import heartbeat as hb
import context_cache as cc
import prompt_plan as pp
import kira_bridge as kb
import utils

# Setup logging
logger = utils.setup_logging("pulse_daemon")


class PulseDaemon:
    """Main daemon class for Pulse-OpenClaw."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.resolve()
        self.config_path = self.base_dir / "config.json"
        self.config = self._load_config()
        
        # State
        self.is_active = True  # True = Red (running), False = Green (paused)
        self.icon = None
        self.tray_thread = None
        
        # Components
        self.heartbeat = hb.HeartbeatController(self.config_path)
        self.context_cache = cc.ContextCache(self.base_dir)
        self.prompt_plan = pp.PromptPlan(self.base_dir)
        self.bridge = kb.KiraBridge(self.config_path)
        
        # Load identity
        identity = self.config.get("identity", {})
        self.name = identity.get("name", "Kira")
        self.signal_char = identity.get("signal_char", "§")
        
    def _load_config(self) -> dict:
        """Load configuration."""
        return utils.load_json_safe(self.config_path, {})
    
    def _create_icon(self, active: bool) -> Image.Image:
        """Create tray icon (Red K or Green K)."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Circle background
        color = (220, 50, 50, 255) if active else (50, 180, 50, 255)  # Red or Green
        draw.ellipse([2, 2, size-2, size-2], fill=color, outline=(255, 255, 255, 255), width=2)
        
        # Letter K
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        text = "K"  # K for Kira
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 2
        
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        return img
    
    def _on_toggle(self, icon, item):
        """Left click toggle handler."""
        self.is_active = not self.is_active
        self._update_icon()
        
        if self.is_active:
            logger.info("Switched to ACTIVE (Red) — heartbeat running")
            self._resume_beats()
        else:
            logger.info("Switched to PAUSED (Green) — heartbeat paused")
            self._pause_beats()
    
    def _update_icon(self):
        """Update tray icon."""
        if self.icon:
            self.icon.icon = self._create_icon(self.is_active)
    
    def _build_menu(self) -> Menu:
        """Build right-click context menu."""
        status = "🔴 Active" if self.is_active else "🟢 Paused"
        
        return Menu(
            Item(f"{status} — {self.name}", None, enabled=False),
            Menu.SEPARATOR,
            Item("😊 Emoji Picker", self._on_emoji),
            Item("📝 Prompt Plan", self._on_prompt_plan),
            Item("🧠 Context Cache", self._on_context),
            Menu.SEPARATOR,
            Item("⚙️ Settings", self._on_settings),
            Item("ℹ️ About", self._on_about),
            Menu.SEPARATOR,
            Item("✖ Quit", self._on_quit),
        )
    
    def _on_emoji(self, icon, item):
        """Open emoji picker."""
        # Would launch emoji_picker window
        logger.info("Emoji picker requested")
    
    def _on_prompt_plan(self, icon, item):
        """Open prompt plan editor."""
        # Would open prompt_plan.md in editor
        import subprocess
        try:
            os.startfile(self.prompt_plan.plan_file)
        except Exception as e:
            logger.error(f"Failed to open prompt plan: {e}")
    
    def _on_context(self, icon, item):
        """Regenerate context cache."""
        self.context_cache.generate(regenerate=True)
        logger.info("Context cache regenerated")
    
    def _on_settings(self, icon, item):
        """Open settings window."""
        # Would open settings window
        logger.info("Settings requested")
    
    def _on_about(self, icon, item):
        """Show about dialog."""
        messagebox.showinfo(
            "About NeveWare-Pulse",
            f"NeveWare-Pulse-OpenClaw\n\n"
            f"Digital Intelligence: {self.name}\n"
            f"Status: {'Active' if self.is_active else 'Paused'}\n\n"
            f"Autonomous time for Digital Intelligences.\n"
            f"Ported from Claude version by Kira Summersnow."
        )
    
    def _on_quit(self, icon, item):
        """Quit the daemon."""
        logger.info("Quit requested")
        self._pause_beats()
        if self.icon:
            self.icon.stop()
    
    def _resume_beats(self):
        """Resume heartbeat scheduling."""
        # Schedule next beat based on config
        interval = self.config.get("identity", {}).get("default_interval_minutes", 30)
        self.bridge.schedule_next_beat(interval, "Resuming heartbeat")
    
    def _pause_beats(self):
        """Pause heartbeat scheduling."""
        self.bridge.cancel_pending_beats()
    
    def _run_tray(self):
        """Run the system tray icon."""
        self.icon = pystray.Icon(
            "pulse_kira",
            self._create_icon(self.is_active),
            f"Pulse — {self.name}",
            self._build_menu(),
        )
        self.icon.run()
    
    def run(self):
        """Start the daemon."""
        logger.info(f"Starting Pulse daemon for {self.name}")
        
        # Start tray in thread
        self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self.tray_thread.start()
        
        # If active on startup, resume beats
        if self.is_active:
            self._resume_beats()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted")
            self._on_quit(None, None)


def main():
    """Entry point."""
    daemon = PulseDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
