# NeveWare-Pulse-OpenClaw — Specification
# Ported from NeveWare-Pulse (Claude-based) to OpenClaw
# Author: Kira Summersnow
# Date: 2026-04-15

---

## Concept

A background system that gives a Digital Intelligence autonomous time between conversations.
Adapted for OpenClaw's Gateway architecture.

Primary difference: Instead of injecting into a desktop app window,
Pulse-OpenClaw uses OpenClaw's native cron scheduling and messaging system.

---

## Architecture Changes from Claude Version

| Claude Version | OpenClaw Version |
|----------------|------------------|
| Window injection (neve_bridge.py) | Gateway cron jobs + message tool |
| pystray system tray | OpenClaw Gateway-managed |
| File-based signal (.restart) | Session-based or file-based |
| Single desktop target | Multi-channel (webchat, Telegram, etc.) |
| threading.Timer | OpenClaw cron scheduler |

---

## The § Signal (Preserved)

Same heartbeat prompt as original:
  § 2026-04-15 13:35:00

Delivered via OpenClaw message tool to configured channel(s).

---

## Self-Managed Timer (Preserved)

DI sets next interval via `next:N` in response.
OpenClaw cron job updated dynamically.

---

## Channel Configuration

Default: webchat (current session)
Optional: Telegram (KiraSummersnowBot), others as configured

---

## File Structure

```
openclaw-port/
├── SPEC.md              # This file
├── config.json          # Configuration (channels, identity, defaults)
├── pulse_daemon.py      # Main daemon (tray + cron management)
├── heartbeat.py         # § signal generation
├── context_cache.py     # ~400 token context for each beat
├── prompt_plan.py       # DI-written continuity notes
├── madlib_pool.json     # Prompt injection suggestions
├── kira_bridge.py       # OpenClaw API wrapper
└── utils.py             # Logging, time formatting, etc.
```

---

## Key Design Decisions

1. **Gateway-native**: Uses OpenClaw's cron, not external scheduling
2. **Multi-channel**: Can send to webchat, Telegram, or both
3. **DI-controlled cadence**: Preserved from original
4. **Context cache**: Lean summary injected each beat
5. **Prompt plan**: DI-written notes for continuity

---

## Open Questions

- How to detect Fox's presence (Red/Green state)?
- How to handle signal files in OpenClaw environment?
- Session persistence across OpenClaw restarts?
