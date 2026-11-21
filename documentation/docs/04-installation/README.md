# 🛠️ Installation & Setup

You can use Wyoming in your own Python project, deploy it with Docker, or run it as part of Home Assistant via add-ons. It’s designed to be lightweight and embeddable.

---

## 📦 Option 1: From Source (Development)

```bash
git clone https://github.com/rhasspy/wyoming
cd wyoming
pip install .
```

Requirements:
- Python 3.8+
- No external dependencies
- Optional: `aiohttp` for HTTP servers

---

## 🐳 Option 2: Dockerized Services

Many Wyoming-compatible services offer Docker images:

```bash
docker run -p 10200:10200   rhasspy/wyoming-whisper   --uri tcp://0.0.0.0:10200
```

Examples:
- `wyoming-whisper` (ASR)
- `wyoming-piper` (TTS)
- `wyoming-openwakeword` (Wakeword)

---

## 🧠 Option 3: Home Assistant Add-ons

If you're using Home Assistant:

1. Go to **Settings > Add-ons > Add-on Store**
2. Search for:
   - **Piper** (TTS)
   - **Whisper** (ASR)
   - **OpenWakeWord**
3. Install and configure pipeline in **Assist Settings**

Wyoming is used as the protocol between Assist and these services.

---

## 🧪 Option 4: CLI Testing

Use `mic_transcribe.py` to stream audio to a Wyoming ASR server:

```bash
python scripts/mic_transcribe.py   --uri tcp://localhost:10200   --rate 16000 --width 2 --channels 1
```

---

## 🔌 Choosing a URI

Wyoming URIs describe the connection type:

| URI Scheme        | Description                     |
|------------------|---------------------------------|
| `tcp://host:port` | Network socket (cross-host)     |
| `unix:///path`    | Fast local Unix socket          |
| `stdio://`        | Communicate via stdin/stdout    |

---

## 🧰 Useful Tools

- `wyoming-cli`: Minimal Wyoming command-line tool (coming soon)
- `client.py`: Example implementation of a TCP client
- `server.py`: Base class to build custom Wyoming servers

---

## ✅ Test It

After starting a service:

```bash
echo '{"type":"ping"}' | nc localhost 10200
```

You should receive a `pong` response if the server is active.

