# 🌐 Section 06 – HTTP Integration

While Wyoming is optimized for **streaming socket communication**, it also supports basic HTTP interfaces via Flask for environments where streaming is not available or needed.

---

## 🧩 HTTP Services Provided

Wyoming includes three HTTP servers:

| Path | File | Description |
|------|------|-------------|
| `/asr` | `wyoming/http/asr_server.py` | Accepts WAV uploads and returns transcript |
| `/tts` | `wyoming/http/tts_server.py` | Accepts text and returns audio |
| `/intent` | `wyoming/http/intent_server.py` | Accepts text and returns structured intent |

---

## 🧪 Example: Speech-to-Text (ASR)

**Endpoint:** `POST /asr`  
**Content-Type:** `multipart/form-data`  
**Fields:**
- `audio` – WAV file
- `name` – ASR model name (optional)

**Curl Example:**

```bash
curl -F "audio=@sample.wav" http://localhost:5001/asr
```

**Response:**

```json
{ "text": "hello world" }
```

---

## 🗣️ Example: Text-to-Speech (TTS)

**Endpoint:** `POST /tts`  
**Content-Type:** `application/json`

**Payload:**

```json
{ "text": "Hello!", "voice": { "language": "en" } }
```

**Curl Example:**

```bash
curl -X POST http://localhost:5002/tts \
     -H "Content-Type: application/json" \
     -d '{"text":"hello!"}' --output hello.wav
```

---

## 🎯 Example: Intent Recognition

**Endpoint:** `POST /intent`  
**Content-Type:** `application/json`

**Payload:**

```json
{ "text": "Turn off the lights" }
```

**Response:**

```json
{
  "intent": {
    "name": "TurnOff",
    "entities": [ { "name": "device", "value": "lights" } ]
  }
}
```

---

## ⚙️ Running the Servers

Each HTTP server is a standalone Python script and uses Flask. You can run them directly:

```bash
python3 wyoming/http/asr_server.py
python3 wyoming/http/tts_server.py
python3 wyoming/http/intent_server.py
```

---

## 📦 Deployment Notes

- Not optimized for large-scale concurrent users.
- Recommended for local or single-user systems.
- Ideal for Home Assistant Add-ons or debugging Wyoming services.

---

## 🧠 Tip

These HTTP services are **thin wrappers** around Wyoming socket clients.  
They convert HTTP input to Wyoming Events and forward to backend services.

You can modify or extend them to fit your infrastructure.

