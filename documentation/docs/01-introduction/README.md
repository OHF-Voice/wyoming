# 🧠 Introduction to Wyoming

Wyoming is a lightweight, streaming-focused protocol and library designed to connect the components of a privacy-respecting, locally-run voice assistant.

Originally created for [Home Assistant's Year of the Voice](https://www.home-assistant.io/blog/2023/01/11/year-of-the-voice/), Wyoming allows voice interfaces to be built using modular services that speak a common protocol: JSON + optional binary payloads, sent peer-to-peer via TCP, Unix sockets or stdin/stdout.

---

## ✨ What is Wyoming?

- 🧩 A **peer-to-peer event protocol** for audio-based services
- 🔄 Messages consist of structured JSON and optional payloads (e.g. raw audio)
- 📡 Supports **streaming** audio, TTS, wakeword, ASR, NLU, intent handling, and more
- ⚙️ Runs over **TCP sockets, Unix sockets, or standard I/O**
- 💡 Designed to be simple enough for implementation in any language

---

## 🎯 Why Was It Created?

- Replace the legacy MQTT protocol from Snips AI
- Simplify streaming communication between audio services
- Allow seamless integration of different implementations (e.g. Whisper, Piper, Porcupine)
- Work natively with Home Assistant and Rhasspy 3
- Support multi-language, offline voice control without a cloud dependency

---

## 🧑‍💻 Who Is It For?

- Developers of voice components (ASR, TTS, Wakeword, etc.)
- Smart home users wanting to build offline, modular voice control
- Integrators needing a privacy-friendly protocol
- Researchers working on speech systems for underrepresented languages

---

## 🧭 Philosophy and Design Principles

Wyoming was created to solve real-world pain points in building distributed, open voice assistants:

| Principle              | Explanation |
|------------------------|-------------|
| 🔌 Modularity          | Every voice component is a standalone microservice |
| 🔐 Privacy-by-design   | No cloud required, fully local deployment possible |
| ⚡ Streaming-first      | No need to buffer entire recordings – supports real-time |
| 🔄 Simple and hackable | Implementable in a few dozen lines per client/server |
| 🌍 Language-neutral    | Not tied to English; supports multilingual systems |

---

## 🚀 Where is Wyoming Used?

- 🏡 **Home Assistant Voice** (local TTS/ASR pipelines)
- 🧠 **Rhasspy 3** (modular assistant architecture)
- 🔊 **Piper TTS** add-on (used via Wyoming)
- 🧪 Community ASR/TTS/Wakeword services (Whisper, Vosk, Porcupine, etc.)

Wyoming is becoming a standard interface layer for open voice tooling – offering a flexible bridge between diverse services.

