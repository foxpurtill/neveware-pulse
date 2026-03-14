"""madlib_window.py — Standalone Madlib Pool manager for NeveWare-Pulse."""
import sys, tkinter as tk
from pathlib import Path

# neve_dir passed as command-line argument
neve_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'Documents' / 'Neve'
madlib_path = neve_dir / 'madlib-pool.md'

PINNED = [
    'Update memory.json before closing the beat.',
    'Write prompt-plan.md \u2014 leave yourself a thread for next time.',
    'End with \u00a7restart and next:N.',
]

def load_pool():
    if not madlib_path.exists():
        return []
    return [l.strip() for l in madlib_path.read_text(encoding='utf-8').splitlines()
            if l.strip() and not l.strip().startswith('#')]

def save_pool(items):
    header = (
        '# Pulse Madlib Pool\n'
        '# One suggestion per line. Lines starting with # are ignored.\n'
        '# 3-4 lines randomly chosen each beat.\n'
        '# Write in first person/imperative from DI perspective.\n\n'
    )
    madlib_path.write_text(header + '\n'.join(items) + '\n', encoding='utf-8')

items = load_pool()
skip_confirm = [False]
bg = '#1a1a2e'; fg = '#e0e0e0'; ebg = '#16213e'

win = tk.Tk()
win.title('Madlib Pool')
win.configure(bg=bg)
win.geometry('520x540')
win.attributes('-topmost', True)

hdr_f = tk.Frame(win, bg=bg)
hdr_f.pack(fill='x', padx=16, pady=(12, 4))
tk.Label(hdr_f, text='Madlib Pool', bg=bg, fg='#aaaaff',
         font=('Segoe UI', 11, 'bold')).pack(side='left')
cnt_lbl = tk.Label(hdr_f, bg='#222244', fg='#888899',
                   font=('Segoe UI', 8), padx=8, pady=2)
cnt_lbl.pack(side='left', padx=8)
tk.Frame(win, bg='#333355', height=1).pack(fill='x', padx=16)

list_frame = tk.Frame(win, bg=bg)
list_frame.pack(fill='both', expand=True, padx=16, pady=4)
item_rows = []

def update_count():
    cnt_lbl.config(text=f'{len(items)} suggestion{"s" if len(items) != 1 else ""}')

def render():
    for w in item_rows:
        w.destroy()
    item_rows.clear()

    for text in PINNED:
        row = tk.Frame(list_frame, bg='#111122')
        row.pack(fill='x', pady=1)
        tk.Label(row, text='\U0001f512', bg='#111122', fg='#444466',
                 font=('Segoe UI', 10)).pack(side='left', padx=(6, 2))
        tk.Label(row, text=text, bg='#111122', fg='#444466',
                 font=('Segoe UI', 9, 'italic'), anchor='w',
                 wraplength=400).pack(side='left', fill='x', expand=True)
        item_rows.append(row)

    for i, text in enumerate(items):
        row = tk.Frame(list_frame, bg=ebg)
        row.pack(fill='x', pady=1)
        tk.Label(row, text=text, bg=ebg, fg=fg, font=('Segoe UI', 9),
                 anchor='w', wraplength=420).pack(side='left', padx=(8, 4),
                 fill='x', expand=True)

        def make_remove(idx, txt, r):
            def do_remove():
                if skip_confirm[0]:
                    items.pop(idx); render(); update_count(); return
                dlg = tk.Toplevel(win)
                dlg.title('Remove?')
                dlg.configure(bg=bg)
                dlg.attributes('-topmost', True)
                dlg.grab_set()
                tk.Label(dlg, text=f'Remove this suggestion?', bg=bg, fg=fg,
                         font=('Segoe UI', 10, 'bold'), pady=10).pack(padx=16)
                tk.Label(dlg, text=f'"{txt[:60]}"', bg=bg, fg='#888899',
                         font=('Segoe UI', 9, 'italic'),
                         wraplength=320).pack(padx=16)
                da = tk.BooleanVar()
                tk.Checkbutton(dlg, text="don't ask me again", variable=da,
                               bg=bg, fg='#666688', selectcolor=ebg,
                               font=('Segoe UI', 8)).pack(pady=(8, 4))
                bf2 = tk.Frame(dlg, bg=bg)
                bf2.pack(pady=(4, 14))
                def yes():
                    if da.get(): skip_confirm[0] = True
                    dlg.destroy(); items.pop(idx); render(); update_count()
                tk.Button(bf2, text='Cancel', command=dlg.destroy,
                          bg='#222244', fg='#888899', font=('Segoe UI', 9),
                          padx=10, pady=3, bd=0).pack(side='left', padx=4)
                tk.Button(bf2, text='Remove', command=yes,
                          bg='#441122', fg='#ff6666', font=('Segoe UI', 9, 'bold'),
                          padx=10, pady=3, bd=0).pack(side='left', padx=4)
            return do_remove

        tk.Button(row, text='\u2715', command=make_remove(i, text, row),
                  bg=ebg, fg='#555577', font=('Segoe UI', 10), bd=0,
                  cursor='hand2', padx=8, activebackground='#441122',
                  activeforeground='#ff6666').pack(side='right', padx=4)
        item_rows.append(row)
    update_count()

tk.Frame(win, bg='#333355', height=1).pack(fill='x', padx=16, pady=(4, 4))
add_row = tk.Frame(win, bg=bg)
add_row.pack(fill='x', padx=16)
new_var = tk.StringVar()
new_entry = tk.Entry(add_row, textvariable=new_var, bg=ebg, fg=fg,
                     insertbackground=fg, font=('Segoe UI', 9), width=38)
new_entry.pack(side='left', padx=(0, 8), ipady=4)

def do_add():
    val = new_var.get().strip()
    if not val: return
    items.append(val)
    new_var.set('')
    render()
    if item_rows:
        new_row = item_rows[-1]
        def flash(n=0):
            if n < 6:
                c = '#1a2a4a' if n % 2 == 0 else ebg
                try:
                    new_row.configure(bg=c)
                    for child in new_row.winfo_children():
                        child.configure(bg=c)
                except Exception:
                    pass
                win.after(180, lambda: flash(n + 1))
        flash()
    new_entry.focus()

tk.Button(add_row, text='+ Add', command=do_add, bg='#2a2a4a', fg='#aaaacc',
          font=('Segoe UI', 9, 'bold'), padx=12, pady=4, bd=0,
          cursor='hand2').pack(side='left')
new_entry.bind('<Return>', lambda e: do_add())

tk.Frame(win, bg='#333355', height=1).pack(fill='x', padx=16, pady=(6, 4))
bf = tk.Frame(win, bg=bg)
bf.pack(pady=(0, 12))
tk.Button(bf, text='Save', command=lambda: [save_pool(items), win.destroy()],
          bg='#533483', fg='white', font=('Segoe UI', 9, 'bold'),
          padx=18, pady=5, bd=0, cursor='hand2').pack(side='left', padx=6)
tk.Button(bf, text='Cancel', command=win.destroy, bg='#222244', fg='#888899',
          font=('Segoe UI', 9), padx=18, pady=5, bd=0,
          cursor='hand2').pack(side='left', padx=6)

render()
win.mainloop()
