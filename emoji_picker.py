"""
emoji_picker.py — Floating emoji picker for NeveWare-Pulse.

Global hotkey (default Ctrl+Alt+E) opens a small tkinter window.
Click an emoji to inject it at the current cursor position via
pyperclip + pyautogui. Recent emojis are persisted to config.json.
Dismiss with Escape or by clicking outside the window.
"""

import time
import json
import logging
import threading
import tkinter as tk
from tkinter import ttk
import keyboard
import pyperclip
import pyautogui

logger = logging.getLogger(__name__)

# Grid layout
COLS = 10
MAX_RECENT = 20

# Default emoji palette — grouped loosely
DEFAULT_EMOJIS = [
    # Faces & people
    "😀","😊","😄","😂","🥲","😍","🥰","😎","🤔","😐",
    "😮","😯","😲","🥺","😢","😭","😤","😠","🤬","😈",
    "🤗","🤭","🫡","🫠","🥴","😴","🤓","👻","💀","🤖",
    # Hand gestures
    "👍","👎","👋","🤝","👏","🙌","🫶","❤️","💙","💚",
    "💛","💜","🖤","🤍","💔","💯","✨","🔥","⚡","🌟",
    # Nature & animals
    "🌸","🌺","🌻","🍀","🌿","🍃","🦊","🐱","🐶","🐺",
    "🦋","🐝","🌙","☀️","⭐","🌈","☁️","❄️","🌊","🌙",
    # Objects & symbols
    "📖","📝","💡","🔮","🎵","🎶","🎨","🎭","🎮","🏆",
    "💎","🔑","🗝️","📬","📧","💬","🗨️","💭","❓","❗",
    # Food & drink
    "☕","🍵","🧋","🍺","🍷","🍕","🍰","🍩","🍓","🫐",
    # Misc
    "🚀","🛸","🌍","🌏","🎉","🎊","🎁","🪄","⚔️","🛡️",
]


class EmojiPicker:
    def __init__(self, config_path: str, on_close_callback=None):
        self.config_path = config_path
        self.on_close_callback = on_close_callback
        self._window: tk.Tk | None = None
        self._hotkey_registered = False
        self._hotkey = "ctrl+alt+e"

    def load_config(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_recent(self, recent: list):
        try:
            config = self.load_config()
            config["recent_emoji"] = recent[:MAX_RECENT]
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"save_recent: {e}")

    def start(self, hotkey: str = None):
        """Register the global hotkey."""
        if hotkey:
            self._hotkey = hotkey
        if not self._hotkey_registered:
            keyboard.add_hotkey(self._hotkey, self._open_picker, suppress=True)
            self._hotkey_registered = True
            logger.info(f"emoji_picker: hotkey {self._hotkey} registered.")

    def stop(self):
        """Unregister the hotkey."""
        if self._hotkey_registered:
            try:
                keyboard.remove_hotkey(self._hotkey)
            except Exception:
                pass
            self._hotkey_registered = False

    def _open_picker(self):
        """Called on hotkey press — opens the picker window in the main thread."""
        # Schedule via tkinter's thread-safe mechanism if a root exists
        # Otherwise spawn a new Tk window directly
        threading.Thread(target=self._show_window, daemon=True).start()

    def _show_window(self):
        config = self.load_config()
        recent = config.get("recent_emoji", [])
        hotkey_display = self._hotkey.upper()

        root = tk.Tk()
        root.title("Emoji Picker")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#1a1a2e")

        # Position near cursor
        x, y = pyautogui.position()
        root.geometry(f"+{x + 10}+{y + 10}")

        selected = {"emoji": None}

        def pick(emoji):
            selected["emoji"] = emoji
            # Update recent list
            if emoji in recent:
                recent.remove(emoji)
            recent.insert(0, emoji)
            self.save_recent(recent[:MAX_RECENT])
            root.destroy()

        def on_close():
            root.destroy()

        # ESC to dismiss
        root.bind("<Escape>", lambda e: on_close())
        root.bind("<FocusOut>", lambda e: on_close())

        # Title bar
        title_frame = tk.Frame(root, bg="#0f3460", pady=4)
        title_frame.pack(fill="x")
        tk.Label(
            title_frame, text=f"Emoji Picker  ({hotkey_display} to open)",
            bg="#0f3460", fg="#e0e0e0", font=("Segoe UI", 9)
        ).pack(side="left", padx=8)
        tk.Button(
            title_frame, text="✕", bg="#0f3460", fg="#aaaaaa",
            bd=0, font=("Segoe UI", 9), command=on_close,
            activebackground="#c0392b", activeforeground="white"
        ).pack(side="right", padx=4)

        btn_style = {
            "width": 2, "font": ("Segoe UI Emoji", 14),
            "bd": 0, "cursor": "hand2",
            "bg": "#16213e", "activebackground": "#533483",
            "fg": "white", "relief": "flat"
        }

        def make_grid(parent, emojis):
            frame = tk.Frame(parent, bg="#1a1a2e", padx=4, pady=4)
            for i, em in enumerate(emojis):
                r, c = divmod(i, COLS)
                btn = tk.Button(frame, text=em, **btn_style, command=lambda e=em: pick(e))
                btn.grid(row=r, column=c, padx=1, pady=1)
            return frame

        # Recent section
        if recent:
            tk.Label(root, text="Recent", bg="#1a1a2e", fg="#888888",
                     font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(4, 0))
            make_grid(root, recent[:COLS]).pack()
            ttk.Separator(root, orient="horizontal").pack(fill="x", padx=4, pady=2)

        # Main palette
        tk.Label(root, text="All", bg="#1a1a2e", fg="#888888",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        make_grid(root, DEFAULT_EMOJIS).pack()

        root.mainloop()

        # After window closes — inject the selected emoji
        emoji = selected.get("emoji")
        if emoji:
            self._inject_emoji(emoji)

        if self.on_close_callback:
            self.on_close_callback()

    def _inject_emoji(self, emoji: str):
        """Inject emoji at cursor position using clipboard paste."""
        try:
            previous = pyperclip.paste()
            pyperclip.copy(emoji)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.15)
            pyperclip.copy(previous)
        except Exception as e:
            logger.error(f"inject_emoji: {e}")
