# 🏗️ Wyoming System Architecture

Wyoming is designed to act as the connective tissue between small, modular services in a voice assistant system. These services communicate over simple socket-based connections using Wyoming events.

---

## 🧩 Component-Based Design

A full voice assistant can be built from independent components:

```
[Mic] → [Wakeword] → [VAD] → [ASR] → [Intent] → [Handler] → [TTS] → [Speaker]
```

Each component runs independently, speaks the same protocol, and can be swapped out for another.

---

## 🔁 Example Event Flow

Here’s a simplified interaction flow:

1. **Wakeword** detection triggers a pipeline start
2. **VAD** determines when user has stopped speaking
3. **ASR** transcribes the audio stream into text
4. **Intent recognizer** interprets the text into structured meaning
5. **Handler** processes the command and returns a result
6. **TTS** converts the result back to speech

Each stage is loosely coupled, allowing fine-grained control, replacement, and scaling.

---

## 🌐 Communication Methods

Wyoming supports multiple connection types:

| Transport         | Use Case                             |
|------------------|--------------------------------------|
| TCP socket       | Multi-host communication             |
| Unix socket      | Fast local communication             |
| stdin/stdout     | Embedded component process piping    |

All transports speak the exact same protocol format.

---

## 🧱 Microservice Separation

Each voice function lives in its own process:

| Component | Protocol Message Types |
|----------|--------------------------|
| Wakeword | `Detect`, `Detection`    |
| ASR      | `Transcribe`, `Transcript` |
| TTS      | `Synthesize`, `AudioChunk` |
| Intent   | `Recognize`, `Intent`    |
| Handle   | `Handled`, `NotHandled`  |

Each service can:
- Be implemented in any language
- Run on separate machines
- Be restarted/upgraded independently

---

## 🖧 Example Deployment

```
[ESP32 Mic] → Home Assistant Server
              ├── wakeword: wyoming-openwakeword
              ├── asr: wyoming-whisper
              ├── tts: wyoming-piper
              ├── handler: native Assist or custom
              └── speaker: USB audio or Pi audio
```

Everything communicates through Wyoming socket connections.

---

## 🧪 Test Pipelines

For development/testing, you can chain together services locally using Unix or TCP sockets, or embed components with subprocess pipes for easier control.

