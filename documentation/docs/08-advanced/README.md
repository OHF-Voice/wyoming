# 🚀 Section 08 – Advanced Deployment & Tools

This section explores strategies for deploying Wyoming-based systems in real-world environments.

---

## 🐳 Docker Deployment

Each Wyoming-compatible service can be containerized.

### 🧱 Basic Dockerfile Template

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install .

CMD ["python", "your_service.py"]
```

### 🧪 Example Compose

```yaml
version: "3.9"
services:
  whisper-asr:
    build: ./wyoming-faster-whisper
    ports:
      - "10200:10200"

  piper-tts:
    build: ./wyoming-piper
    ports:
      - "5002:5002"
```

---

## 🧠 System Architectures

### 1. 🖥️ Local All-in-One

- All services run on one host (e.g. Raspberry Pi or NUC)
- Pros: simple, fast, no networking
- Cons: resource-limited

### 2. 🌐 Client-Server Model

- Satellites stream to central voice server
- Each component (ASR, TTS, Wake) in separate container

### 3. ☁️ Hybrid Cloud

- Local Wakeword + VAD
- Cloud Whisper for large model accuracy
- WebSocket gateway forwards audio to cloud

---

## 📡 Multiservice Router

You can route events between multiple services using:

- [Rhasspy Hermes MQTT](https://github.com/rhasspy/rhasspy-hermes-app)
- Custom Python proxies
- Home Assistant Assist pipelines

---

## 🧪 Service Discovery

Use `wyoming.zeroconf` to advertise services over mDNS:

```python
from wyoming.zeroconf import publish_service

publish_service("_wyoming._tcp", 10200, name="whisper")
```

Use with `zeroconf` browser tools like:

```bash
avahi-browse _wyoming._tcp -r
```

---

## 🧰 Debugging Tools

### Test Connection

```bash
echo '{"type":"describe"}' | nc localhost 10200
```

### Log Events

```python
from wyoming.event import read_event

while True:
    event = await read_event(reader)
    print("Received", event.type)
```

---

## 🔐 Security Considerations

- Wyoming has **no authentication built-in**
- Use firewall rules or secure tunnel (e.g. NGINX, SSH, VPN)
- Prefer `unix://` sockets for local-only communication

---

## 🧱 Base Image Recommendations

- `python:3.11-slim` for most services
- `debian:bookworm` for services needing `ffmpeg`, `espeak-ng`, etc.
- Always pin model files via SHA or tag

---

## 🧠 Tips

- Run ASR and TTS in separate processes to avoid blocking
- Use `asyncio` or `trio` for concurrency
- Monitor CPU/GPU usage when tuning audio latency

