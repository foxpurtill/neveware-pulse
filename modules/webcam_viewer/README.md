# webcam_viewer

Gives Neve eyes. Opens a live webcam feed via the `@llmindset/mcp-webcam` MCP server, and tells
Claude Desktop that webcam tools are available in every heartbeat.

---

## What it does

- Adds an **Open Webcam** menu item to the tray
- Clicking it opens `http://localhost:3333` in your browser (the MCP webcam viewer)
- On enable, checks whether the MCP server is reachable and warns if it isn't
- Includes `webcam_available: true` in heartbeat `di_instructions` so Neve knows she can see

---

## Prerequisites

### 1. Install the MCP server (already done on Fox's machine)

```
npm install -g @llmindset/mcp-webcam
```

### 2. Register it in Claude Desktop config

The webcam server is already registered in `claude_desktop_config.json`:

```json
"webcam": {
  "command": "npx",
  "args": ["-y", "@llmindset/mcp-webcam"]
}
```

If setting up on a new machine, add that block to the `mcpServers` section of:
`%APPDATA%\Claude\claude_desktop_config.json`

### 3. Restart Claude Desktop

After editing the config, restart Claude Desktop. The hammer icon (🔨) in the chat
input confirms MCP tools loaded. You should see webcam tools available.

---

## Pause state

When Pulse is **paused (Red)**, the webcam menu item is still visible but Neve won't
actively watch — she only processes what she's asked. Full pause-aware behaviour
(auto-suspend on Red, resume on Green) is planned for a future update.

---

## Troubleshooting

**"MCP server not found at http://localhost:3333"** — The webcam server isn't running.
Claude Desktop starts it automatically when configured correctly. Check that:
- The config entry is correct
- Claude Desktop was fully restarted after config change
- `npx` is on your PATH (run `npx --version` to verify)

**Browser opens but shows blank / error** — Allow camera access when the browser prompts.
