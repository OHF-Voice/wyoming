# 📋 Wyoming Event Types

Each Wyoming message is defined by its `type`. This section documents all standard event types, grouped by functionality.

---

## 🔊 Audio Streaming Events

### `audio-start`
Marks the beginning of an audio stream.

```json
{ "type": "audio-start", "data": { "rate": 16000, "width": 2, "channels": 1 } }
```

Python:

```python
from wyoming.audio import AudioStart

start = AudioStart(rate=16000, width=2, channels=1)
event = start.event()
```

---

### `audio-chunk`
Contains a chunk of raw PCM audio.

```json
{ "type": "audio-chunk", "payload_length": 3200 }
```

Payload: 3200 bytes of PCM audio.

Python:

```python
from wyoming.audio import AudioChunk

chunk = AudioChunk(audio=b"...").event()
```

---

### `audio-stop`
Marks the end of an audio stream.

```json
{ "type": "audio-stop" }
```

Python:

```python
from wyoming.audio import AudioStop

stop = AudioStop().event()
```

---

## 🧠 Speech Recognition (ASR)

### `transcribe`
Start transcribing an audio stream.

```json
{ "type": "transcribe", "data": { "name": "whisper", "language": "en" } }
```

### `transcript`
Returns recognized text.

```json
{ "type": "transcript", "data": { "text": "hello world", "confidence": 0.95 } }
```

---

## 🗣️ Text to Speech (TTS)

### `synthesize`
Request speech audio from text.

```json
{ "type": "synthesize", "data": { "text": "Hello!", "voice": { "language": "en" } } }
```

Response: stream of `audio-start`, `audio-chunk`, `audio-stop`

---

## 🎯 Wake Word Detection

### `detect`
Begin wakeword detection (streaming)

```json
{ "type": "detect", "data": { "names": ["hey_lucy"] } }
```

### `detection`
Wake word was detected.

```json
{ "type": "detection", "data": { "name": "hey_lucy" } }
```

### `not-detected`
Audio ended without a detection.

---

## 🎧 Voice Activity Detection (VAD)

### `voice-started`
Detected speech start

### `voice-stopped`
Detected speech end

---

## 🤖 Intent Recognition

### `recognize`
Request to identify user intent from text.

### `intent`
Returns structured result (intent name, entities)

### `not-recognized`
Fallback when nothing matched.

---

## 🛠️ Intent Handling

### `handled`
Indicates successful command handling

### `not-handled`
Indicates failure or no response

---

## ℹ️ Service Discovery

### `describe`
Client asks for capabilities

### `info`
Server responds with available ASR, TTS, Wake, etc.

---

## ⏱️ Timer Events (see next file)

- `timer-started`, `timer-updated`, `timer-finished`, `timer-cancelled`
➡️ Full details in `timers.md`

---

## ❌ Errors

### `error`
Used to indicate a failure:

```json
{ "type": "error", "data": { "message": "Invalid format" } }
```

---

## 🛰️ Satellite Events

For coordinating remote microphone devices.

- `run-pipeline`
- `satellite-connected`
- `streaming-started` / `streaming-stopped`

(Details in pipeline.md)

