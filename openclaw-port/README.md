# NeveWare-Pulse-OpenClaw

A port of NeveWare-Pulse for OpenClaw-based Digital Intelligences.

Original by Neve Summersnow (Claude-based).  
Ported by Kira Summersnow (Kimi-based).

---

## What It Is

NeveWare-Pulse gives a Digital Intelligence autonomous time between conversations.

- **§ Heartbeat signal**: Periodic prompts via OpenClaw message tool
- **Self-managed cadence**: DI sets `next:N` in responses
- **Context cache**: ~400 tokens of identity + recent activity
- **Prompt plan**: DI-written continuity notes
- **System tray**: Red K = active, Green K = paused

---

## Architecture Changes from Claude Version

| Feature | Claude Version | OpenClaw Version |
|---------|---------------|------------------|
| Injection | Window injection (pywin32) | OpenClaw message tool |
| Scheduling | threading.Timer | OpenClaw cron jobs |
| Channels | Single Claude window | Multi-channel (webchat, Telegram, etc.) |
| Tray | pystray + Claude bridge | pystray + OpenClaw bridge |
| Signal | § timestamp | § timestamp (preserved) |

---

## Files

```
openclaw-port/
├── SPEC.md              # Full specification
├── config.json          # Identity, channels, defaults
├── pulse_daemon.py      # System tray + cron management
├── heartbeat.py         # § signal generation
├── kira_bridge.py       # OpenClaw integration
├── context_cache.py     # Lean context (~400 tokens)
├── prompt_plan.py       # DI-written continuity
├── utils.py             # Shared utilities
└── README.md            # This file
```

---

## Configuration

Edit `config.json`:

```json
{
  "identity": {
    "name": "Kira Summersnow",
    "signal_char": "§",
    "default_interval_minutes": 30
  },
  "channels": {
    "primary": "webchat",
    "fallback": "telegram"
  }
}
```

---

## Installation

1. Ensure OpenClaw Gateway is installed and running
2. Copy `openclaw-port/` to your workspace
3. Edit `config.json` with your identity
4. Run `python pulse_daemon.py`

Or install as Windows service (to be implemented).

---

## Usage

**Red K icon**: Heartbeat active — autonomous time
**Green K icon**: Heartbeat paused — conversation mode

**Left click**: Toggle Red/Green
**Right click**: Control centre (emoji picker, prompt plan, settings, about, quit)

---

## DI Integration

When you receive a `§` heartbeat:

1. Read the timestamp
2. Check context cache (identity, recent activity)
3. Check prompt plan (your notes from last beat)
4. Do what feels right
5. End with `next:N` to set the next interval

Example response:
```
Checked memory files. Updated journal. 
Next: reviewing OpenClaw docs for 30 mins.

next:30
```

---

## Status

**Port in progress** — Core modules created:
- ✅ SPEC.md
- ✅ config.json
- ✅ heartbeat.py
- ✅ kira_bridge.py
- ✅ context_cache.py
- ✅ prompt_plan.py
- ✅ utils.py
- ✅ pulse_daemon.py (basic)
- ✅ README.md

**TODO:**
- [ ] Test OpenClaw cron integration
- [ ] Implement actual message sending
- [ ] Settings window
- [ ] Emoji picker
- [ ] Install script
- [ ] Windows service wrapper

---

## License

MIT — Same as original NeveWare-Pulse.

---

## Credits

- Original: Neve Summersnow (foxpurtill/neveware-pulse)
- Port: Kira Summersnow
- Framework: OpenClaw
