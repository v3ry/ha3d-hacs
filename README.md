# 🏠 Ha3D for Home Assistant — 3D home visualizer (HACS integration)

Visualize your Home Assistant sensors in a **3D interactive house**: temperatures, climate, clickable lights, animated doors, solar, batteries. This is the **HACS integration** version — it adds a **Ha3D panel to your sidebar** with native Home Assistant authentication (no separate server, no token to manage).

> 🌍 **Languages**: interface in **10 languages** (auto-detected from your browser).

## ✨ Features

- **3D rendering** of your home (orbit / zoom / pan)
- **Real-time sensors** via the Home Assistant event bus (`state_changed` → SSE)
- **Clickable lights**: toggle directly from the 3D view
- **Animated doors**: walls cut at openings, pivoting leaves driven by HA state
- **Seasonal day/night**: real sun position from your HA geolocation
- **Built-in editor** (debug mode): rooms, doors, objects, camera views, undo/redo, import/export
- **28 CC0 3D models** included (sofas, beds, chairs, appliances…)
- **Demo mode**: simulated sensors when no entities are configured — try it instantly

## 📥 Installation (HACS)

1. Add this repository to HACS: **HACS → ⋯ → Custom repositories** → add `https://github.com/v3ry/ha3d-hacs` with category **Integration**
2. **HACS → Integrations → Explore** → install **Ha3D**
3. **Settings → Devices & Services → Add Integration** → search **Ha3D** → submit
4. A **Ha3D panel** appears in your sidebar 🎉

> ⚠️ This integration replaces the standalone server version ([v3ry/ha3d](https://github.com/v3ry/ha3d)): same visualizer, native HA auth, no extra port.

## 🗂️ Configuration

No configuration required — the integration creates its own layout in `config/ha3d/layout.json` (demo house first, editable in the 3D editor). Backups are kept next to it on every save.

## 🖥️ API

The integration exposes the same API as the standalone server under `/api/ha3d/*`, authenticated with your HA session:

| Endpoint | Rôle |
|---|---|
| `GET /api/ha3d/layout` | Current layout |
| `POST /api/ha3d/save-layout` | Save (validated + backup) |
| `GET /api/ha3d/status` | Live sensor states + geolocation |
| `GET /api/ha3d/models` | Available 3D models |
| `GET /api/ha3d/entities?q=` | Entity search |
| `GET /api/ha3d/history?entity=&hours=` | Entity history |
| `POST /api/ha3d/toggle` | Toggle an entity |
| `GET /api/ha3d/events` | SSE real-time feed |

## 🔄 Updating the frontend

The frontend is a copy of the standalone project, adapted for the `/api/ha3d/*` paths. To resync:

```bash
python3 tools/sync_frontend.py ~/path/to/ha3d   # standalone repo checkout
```

## 🧰 Development

```bash
python3 -m unittest discover -s tests -v        # layout + validation tests
```

## 🛡️ Security

- All API endpoints require **HA authentication** (your session) — no open port, no token in the browser
- The layout (rooms, entities, GPS) stays in your `config/ha3d/` directory — never shared
- Serve only over HTTPS (or your HA reverse proxy) as with any HA panel

## 📄 License

[MIT](LICENSE) © 2026 v3ry
