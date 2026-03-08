# mic_listener

Gives Neve ears. Connects to the Audio MCP Server (GongRzhe/Audio-MCP-Server), which lets
Claude Desktop record from the microphone, list audio devices, and play back audio.

---

## What it does

- Tells Claude Desktop that audio tools are available
- Includes `mic_available: true` in heartbeat `di_instructions`
- Neve can then call `record_audio`, `list_audio_devices`, `playback_recording` etc.
  from within any conversation

---

## Prerequisites

### 1. Clone and install the MCP server (already done on Fox's machine)

```
git clone https://github.com/GongRzhe/Audio-MCP-Server.git C:\Code\Audio-MCP-Server
cd C:\Code\Audio-MCP-Server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Register it in Claude Desktop config

Already registered in `claude_desktop_config.json` for Fox's machine:

```json
"audio-interface": {
  "command": "C:\\Code\\Audio-MCP-Server\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Code\\Audio-MCP-Server\\audio_server.py"],
  "env": {
    "PYTHONPATH": "C:\\Code\\Audio-MCP-Server"
  }
}
```

For a new machine, update the paths to match where you cloned the repo,
and add to the `mcpServers` section of `%APPDATA%\Claude\claude_desktop_config.json`.

### 3. Restart Claude Desktop

Restart fully after editing config. The 🔨 icon confirms MCP tools loaded.
You should see `record_audio`, `list_audio_devices`, `playback_recording` in the tools list.

---

## Available tools (once connected)

| Tool | What it does |
|------|-------------|
| `list_audio_devices` | Shows all mics and speakers on the system |
| `record_audio` | Records from mic (configurable duration, device) |
| `playback_recording` | Plays back the most recent recording |
| `play_audio_file` | Plays a file through speakers |

---

## Pause state

When Pulse is **paused (Red)**, mic_listener doesn't actively record — Neve only
uses audio tools when directly asked. Full pause-aware behaviour (auto-suspend on Red)
is planned for a future update.

---

## Troubleshooting

**No audio tools in Claude Desktop** — Confirm the venv python path is correct.
Run: `C:\Code\Audio-MCP-Server\.venv\Scripts\python.exe --version` — should return Python 3.x.

**PortAudio / sounddevice error** — On Windows this usually self-resolves. If not:
`pip install sounddevice --upgrade` inside the venv.

**Recording permission denied** — Allow microphone access in Windows Settings > Privacy > Microphone.
