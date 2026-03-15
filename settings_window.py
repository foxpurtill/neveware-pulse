"""settings_window.py — Standalone settings window for NeveWare-Pulse."""
import json, tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

bg = '#1a1a2e'; fg = '#e0e0e0'; entry_bg = '#16213e'; adv_bg = '#12122a'

win = tk.Tk()
win.title('NeveWare-Pulse \u2014 Settings')
win.configure(bg=bg)
win.resizable(False, True)
win.attributes('-topmost', True)

# ── Scrollable canvas ────────────────────────────────────────────────────────
outer = tk.Frame(win, bg=bg)
outer.pack(fill='both', expand=True)
canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, width=560)
vsb = tk.Scrollbar(outer, orient='vertical', command=canvas.yview)
canvas.configure(yscrollcommand=vsb.set)
vsb.pack(side='right', fill='y')
canvas.pack(side='left', fill='both', expand=True)
main = tk.Frame(canvas, bg=bg)
main_id = canvas.create_window((0, 0), window=main, anchor='nw')
def _on_frame(e): canvas.configure(scrollregion=canvas.bbox('all'))
def _on_canvas(e): canvas.itemconfig(main_id, width=e.width)
def _on_wheel(e): canvas.yview_scroll(int(-1*(e.delta/120)), 'units')
main.bind('<Configure>', _on_frame)
canvas.bind('<Configure>', _on_canvas)
canvas.bind_all('<MouseWheel>', _on_wheel)

# ── Helpers ──────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tip = None
        widget.bind('<Enter>', self.show); widget.bind('<Leave>', self.hide)
    def show(self, _=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f'+{x}+{y}')
        tk.Label(self.tip, text=self.text, bg='#2a2a4a', fg='#ccccee',
                 font=('Segoe UI', 8), relief='flat', padx=8, pady=4,
                 wraplength=300, justify='left').pack()
    def hide(self, _=None):
        if self.tip: self.tip.destroy(); self.tip = None

def divider(parent):
    tk.Frame(parent, bg='#333355', height=1).pack(fill='x', padx=10, pady=(10, 4))

def field_row(parent, label, var, tip, bg_=None, show=None):
    """Single label + entry + ⓘ row using pack inside a frame."""
    b = bg_ or bg
    row = tk.Frame(parent, bg=b)
    row.pack(fill='x', padx=10, pady=2)
    tk.Label(row, text=label, bg=b, fg=fg, font=('Segoe UI', 9),
             width=20, anchor='e').pack(side='left')
    kw = dict(textvariable=var, bg='#0e0e22' if bg_ else entry_bg, fg=fg,
              insertbackground=fg, width=30, font=('Segoe UI', 9))
    if show is not None: kw['show'] = show
    ent = tk.Entry(row, **kw)
    ent.pack(side='left', padx=(4, 2))
    lbl = tk.Label(row, text='\u24d8', bg=b, fg='#555588',
                   font=('Segoe UI', 10), cursor='question_arrow')
    lbl.pack(side='left', padx=(2, 0))
    Tooltip(lbl, tip)
    return ent

# ── Header ───────────────────────────────────────────────────────────────────
tk.Label(main, text='NeveWare-Pulse Settings', bg=bg, fg='#aaaaff',
         font=('Segoe UI', 12, 'bold')).pack(pady=(14, 8))

# ── Section 1: Standard fields ───────────────────────────────────────────────
FIELDS = [
    ('Icon Letter',            'icon_letter',              'Single letter shown on the tray icon. Change to your DI\'s initial.'),
    ('Active Colour (hex)',    'active_color',             'Tray icon colour when heartbeat is running. Default #FF4444 (red).'),
    ('Inactive Colour (hex)',  'inactive_color',           'Tray icon colour when paused. Default #44BB44 (green).'),
    ('Heartbeat Character',    'heartbeat_character',      'Signal character sent each beat. Default: §'),
    ('Default Interval (min)', 'default_interval_minutes', 'Fallback interval if the DI doesn\'t write next:N in their response.'),
    ('Emoji Hotkey',           'emoji_hotkey',             'System-wide hotkey to open the emoji picker. Default: Ctrl+Alt+E.'),
    ('AI Name',                'ai_name',                  'Your DI\'s name — shown in tray header and heartbeat prompts.'),
    ('Email Address',          'email_address',            'The DI\'s email address. Used by the email_watcher module.'),
    ('ElevenLabs Voice ID',    'elevenlabs_voice_id',      'Voice ID from ElevenLabs.\nFind yours at elevenlabs.io/voice-library\nExample: 21m00Tcm4TlvDq8ikWAM (Rachel)'),
]
entries = {}
for label, key, tip in FIELDS:
    var = tk.StringVar(value=str(config.get(key, '')))
    field_row(main, label, var, tip)
    entries[key] = var

# Defibrillator checkbox
cb_row = tk.Frame(main, bg=bg)
cb_row.pack(fill='x', padx=10, pady=(6, 2))
dv = tk.BooleanVar(value=config.get('defib_restore_last_state', True))
tk.Checkbutton(cb_row, text='Restore last state after Defibrillator recovery',
               variable=dv, bg=bg, fg=fg, selectcolor=entry_bg,
               activebackground=bg, font=('Segoe UI', 9)).pack(side='left', padx=22)

# ── Section 2: Advanced Settings (collapsible) ───────────────────────────────
divider(main)

adv_open = tk.BooleanVar(value=False)

# Toggle button
adv_btn = tk.Button(main, text='▼  Advanced Settings',
                    bg=adv_bg, fg='#8888bb', font=('Segoe UI', 9),
                    relief='flat', bd=0, cursor='hand2', anchor='w', padx=10, pady=5)
adv_btn.pack(fill='x', padx=10, pady=(0, 2))

# Content frame — packed immediately after the button, hidden by default
adv_frame = tk.Frame(main, bg=adv_bg)
# (not packed yet — toggle_advanced handles this)

def toggle_advanced():
    if adv_open.get():
        adv_frame.pack(fill='x', padx=10, pady=(0, 6), after=adv_btn)
        adv_btn.config(text='▲  Advanced Settings')
    else:
        adv_frame.pack_forget()
        adv_btn.config(text='▼  Advanced Settings')
adv_btn.config(command=lambda: [adv_open.set(not adv_open.get()), toggle_advanced()])

# API key rows
adv_entries = {}
ADV_FIELDS = [
    ('ElevenLabs API Key', 'elevenlabs_api_key', 'ElevenLabs API key for voice output.\nGet yours at elevenlabs.io/app'),
]
for label, key, tip in ADV_FIELDS:
    var = tk.StringVar(value=str(config.get(key, '')))
    ent = field_row(adv_frame, label, var, tip, bg_=adv_bg, show='*')
    # Eye toggle — placed on the same row by patching its parent frame
    eye_var = tk.BooleanVar(value=False)
    def _make_eye(e=ent, ev=eye_var):
        def _t(): e.config(show='' if ev.get() else '*')
        return _t
    # Find the last child of ent's parent and add eye button after ⓘ
    parent_row = ent.master
    tk.Checkbutton(parent_row, text='👁', variable=eye_var,
                   command=_make_eye(ent, eye_var),
                   bg=adv_bg, selectcolor=adv_bg, activebackground=adv_bg,
                   font=('Segoe UI', 10), relief='flat', bd=0,
                   cursor='hand2', indicatoron=False).pack(side='left', padx=2)
    adv_entries[key] = var

# Claude app path row
claude_path_var = tk.StringVar(value=config.get('claude_app_path', ''))
cp_outer = tk.Frame(adv_frame, bg=adv_bg)
cp_outer.pack(fill='x', padx=10, pady=2)
tk.Label(cp_outer, text='Claude App Path', bg=adv_bg, fg=fg,
         font=('Segoe UI', 9), width=20, anchor='e').pack(side='left')
tk.Entry(cp_outer, textvariable=claude_path_var, bg='#0e0e22', fg=fg,
         insertbackground=fg, width=24, font=('Segoe UI', 9)).pack(side='left', padx=(4, 2))

def browse_claude():
    p = filedialog.askopenfilename(
        title='Locate Claude App', parent=win,
        filetypes=[('Executable', '*.exe'), ('All files', '*.*')],
        initialdir=str(Path.home() / 'AppData' / 'Local'))
    if p: claude_path_var.set(p)

def verify_claude():
    p = claude_path_var.get().strip()
    if not p:
        messagebox.showwarning('Claude Path', 'No path set. Use Browse to locate Claude.exe.', parent=win)
        return
    if Path(p).exists():
        messagebox.showinfo('Claude Path', f'\u2713 Found:\n{p}', parent=win)
    else:
        messagebox.showerror('Claude Path',
            f'\u2717 Not found:\n{p}\n\nUse Browse to locate the correct executable.', parent=win)

tk.Button(cp_outer, text='Browse', command=browse_claude, bg='#2a2a4a', fg='#aaaacc',
          font=('Segoe UI', 8), padx=8, pady=2, bd=0, cursor='hand2').pack(side='left', padx=2)
tk.Button(cp_outer, text='Verify', command=verify_claude, bg='#1a3a2a', fg='#66cc88',
          font=('Segoe UI', 8), padx=8, pady=2, bd=0, cursor='hand2').pack(side='left', padx=2)
cp_il = tk.Label(cp_outer, text='\u24d8', bg=adv_bg, fg='#555588',
                 font=('Segoe UI', 10), cursor='question_arrow')
cp_il.pack(side='left', padx=(2, 0))
Tooltip(cp_il, 'Full path to Claude.exe.\nUsed to launch or focus Claude for heartbeat injection.\nTypically in AppData\\Local\\AnthropicClaude\\')

# ── Section 3: Modules ───────────────────────────────────────────────────────
divider(main)
tk.Label(main, text='Modules', bg=bg, fg='#aaaaff',
         font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=14, pady=(2, 0))
tk.Label(main, text='Enable or disable optional modules. Changes take effect after restart.',
         bg=bg, fg='#555577', font=('Segoe UI', 8, 'italic')
         ).pack(anchor='w', padx=14, pady=(0, 4))

MODULES = [
    ('email_watcher', 'Email Watcher',  'Checks inbox each heartbeat and shows a toast for new mail.'),
    ('voice_output',  'Voice Output',   'Speaks DI responses aloud via ElevenLabs TTS + ffplay.\nRequires ElevenLabs API key in Advanced Settings.'),
    ('webcam_viewer', 'Webcam Viewer',  'Adds a tray menu item to open the webcam feed at localhost:3333.'),
    ('mic_listener',  'Mic Listener',   'Listens via microphone and injects spoken context into the heartbeat prompt via Whisper.'),
    ('neve_memory',   'Neve Memory',    'Backs up memory.json to GitHub on each heartbeat.\nRequires neve_memory module files installed.'),
]
module_vars = {}
mods_cfg = config.get('modules', {})
for mod_key, mod_label, mod_tip in MODULES:
    var = tk.BooleanVar(value=mods_cfg.get(mod_key, {}).get('enabled', False))
    row = tk.Frame(main, bg=bg)
    row.pack(fill='x', padx=14, pady=1)
    tk.Checkbutton(row, text=mod_label, variable=var, bg=bg, fg=fg,
                   selectcolor=entry_bg, activebackground=bg,
                   font=('Segoe UI', 9)).pack(side='left')
    il = tk.Label(row, text='\u24d8', bg=bg, fg='#555588',
                  font=('Segoe UI', 10), cursor='question_arrow')
    il.pack(side='left', padx=4)
    Tooltip(il, mod_tip)
    module_vars[mod_key] = var

# ── Section 4: Buttons ───────────────────────────────────────────────────────
divider(main)

DEFAULTS = {
    'icon_letter': 'N', 'active_color': '#FF4444', 'inactive_color': '#44BB44',
    'heartbeat_character': '\u00a7', 'default_interval_minutes': '30',
    'emoji_hotkey': 'ctrl+alt+e', 'ai_name': 'Neve',
    'email_address': '', 'elevenlabs_voice_id': '',
}

def reset_defaults():
    if not messagebox.askyesno(
        'Reset to Defaults',
        'Reset all standard settings to their defaults?\n\n'
        'API keys, module states and Claude path will not be changed.',
        parent=win): return
    for key, val in DEFAULTS.items():
        if key in entries: entries[key].set(val)
    dv.set(True)

def save():
    for key, var in entries.items():
        val = var.get()
        config[key] = int(val) if key == 'default_interval_minutes' else val
    config['defib_restore_last_state'] = dv.get()
    for key, var in adv_entries.items():
        val = var.get().strip()
        if val: config[key] = val
    config['claude_app_path'] = claude_path_var.get().strip()
    if config.get('elevenlabs_voice_id'):
        config.setdefault('modules', {}).setdefault('voice_output', {})['voice_id'] = config['elevenlabs_voice_id']
    if config.get('elevenlabs_api_key'):
        config.setdefault('modules', {}).setdefault('voice_output', {})['api_key'] = config['elevenlabs_api_key']
    for mod_key, var in module_vars.items():
        config.setdefault('modules', {}).setdefault(mod_key, {})['enabled'] = var.get()
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    win.destroy()

bf = tk.Frame(main, bg=bg)
bf.pack(pady=(4, 16))
tk.Button(bf, text='Save', command=save, bg='#533483', fg='white',
          font=('Segoe UI', 9, 'bold'), padx=16, pady=5, bd=0,
          cursor='hand2').pack(side='left', padx=6)
tk.Button(bf, text='Reset to Defaults', command=reset_defaults,
          bg='#2a2a4a', fg='#aaaacc', font=('Segoe UI', 9),
          padx=12, pady=5, bd=0, cursor='hand2').pack(side='left', padx=6)
tk.Button(bf, text='Cancel', command=win.destroy, bg='#333355', fg=fg,
          font=('Segoe UI', 9), padx=16, pady=5, bd=0,
          cursor='hand2').pack(side='left', padx=6)

win.geometry('580x640')
win.update_idletasks()
win.mainloop()
