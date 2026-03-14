"""settings_window.py — Standalone settings window for NeveWare-Pulse."""
import json, sys, tkinter as tk
from tkinter import filedialog
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

bg = '#1a1a2e'; fg = '#e0e0e0'; entry_bg = '#16213e'
win = tk.Tk()
win.title('NeveWare-Pulse \u2014 Settings')
win.configure(bg=bg)
win.resizable(False, False)
win.attributes('-topmost', True)

tk.Label(win, text='NeveWare-Pulse Settings', bg=bg, fg='#aaaaff',
         font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=(10,4))

fields = [
    ('Icon Letter',            'icon_letter'),
    ('Active Colour (hex)',    'active_color'),
    ('Inactive Colour (hex)',  'inactive_color'),
    ('Heartbeat Character',    'heartbeat_character'),
    ('Default Interval (min)', 'default_interval_minutes'),
    ('Emoji Hotkey',           'emoji_hotkey'),
    ('AI Name',                'ai_name'),
    ('Email Address',          'email_address'),
    ('ElevenLabs Voice ID',    'elevenlabs_voice_id'),
]

entries = {}
pad = {'padx': 8, 'pady': 4}
for i, (label, key) in enumerate(fields, start=1):
    tk.Label(win, text=label, bg=bg, fg=fg, font=('Segoe UI', 9),
             anchor='e').grid(row=i, column=0, sticky='e', **pad)
    var = tk.StringVar(value=str(config.get(key, '')))
    tk.Entry(win, textvariable=var, bg=entry_bg, fg=fg, insertbackground=fg,
             width=28, font=('Segoe UI', 9)).grid(row=i, column=1, sticky='w', **pad)
    entries[key] = var

r = len(fields) + 1
dv = tk.BooleanVar(value=config.get('defib_restore_last_state', True))
tk.Checkbutton(win, text='Restore last state after Defibrillator recovery',
               variable=dv, bg=bg, fg=fg, selectcolor=entry_bg,
               activebackground=bg, activeforeground=fg,
               font=('Segoe UI', 9)).grid(row=r, column=0, columnspan=2,
               sticky='w', padx=8, pady=(8, 2))
r += 1

def save():
    for key, var in entries.items():
        val = var.get()
        if key == 'default_interval_minutes':
            try: config[key] = int(val)
            except: pass
        else:
            config[key] = val
    config['defib_restore_last_state'] = dv.get()
    if config.get('elevenlabs_voice_id'):
        config.setdefault('modules', {}).setdefault('voice_output', {})['voice_id'] = config['elevenlabs_voice_id']
    if config.get('elevenlabs_api_key'):
        config.setdefault('modules', {}).setdefault('voice_output', {})['api_key'] = config['elevenlabs_api_key']
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    win.destroy()

bf = tk.Frame(win, bg=bg)
bf.grid(row=r, column=0, columnspan=2, pady=10)
tk.Button(bf, text='Save', command=save, bg='#533483', fg='white',
          font=('Segoe UI', 9, 'bold'), padx=16, pady=4, bd=0,
          cursor='hand2').pack(side='left', padx=6)
tk.Button(bf, text='Cancel', command=win.destroy, bg='#333355', fg=fg,
          font=('Segoe UI', 9), padx=16, pady=4, bd=0,
          cursor='hand2').pack(side='left', padx=6)

win.mainloop()
