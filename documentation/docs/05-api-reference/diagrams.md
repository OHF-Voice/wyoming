# 🔁 Event Flow Diagrams

This section visualizes the communication between Wyoming components using **Mermaid sequence diagrams**.

---

## 🎙️ Speech-to-Text (ASR)

```mermaid
sequenceDiagram
    participant Client
    participant ASR

    Client->>ASR: transcribe
    Client->>ASR: audio-start
    loop while speaking
        Client->>ASR: audio-chunk
    end
    Client->>ASR: audio-stop
    ASR-->>Client: transcript
```

---

## 🗣️ Text-to-Speech (TTS)

```mermaid
sequenceDiagram
    participant Client
    participant TTS

    Client->>TTS: synthesize
    TTS-->>Client: audio-start
    loop while speaking
        TTS-->>Client: audio-chunk
    end
    TTS-->>Client: audio-stop
```

---

## 🚨 Wake Word Detection

```mermaid
sequenceDiagram
    participant Client
    participant Wakeword

    Client->>Wakeword: detect
    Client->>Wakeword: audio-start
    loop stream
        Client->>Wakeword: audio-chunk
        alt detected
            Wakeword-->>Client: detection
        end
    end
    Client->>Wakeword: audio-stop
    Wakeword-->>Client: not-detected
```

---

## 🎧 Voice Activity Detection

```mermaid
sequenceDiagram
    participant Client
    participant VAD

    loop stream
        Client->>VAD: audio-chunk
        alt speech starts
            VAD-->>Client: voice-started
        end
        alt speech ends
            VAD-->>Client: voice-stopped
        end
    end
```

---

## ⏱️ Timer Pipeline

```mermaid
sequenceDiagram
    participant User
    participant ASR
    participant Intent
    participant Handler
    participant Timer

    User->>ASR: "Set a timer for 5 minutes"
    ASR->>Intent: transcribe
    Intent->>Handler: parsed intent
    Handler->>Timer: timer-started
    Timer-->>Handler: timer-confirmation
```

---

## 🔁 Full Pipeline Flow

```mermaid
sequenceDiagram
    participant Mic
    participant Wake
    participant VAD
    participant ASR
    participant Intent
    participant Handler
    participant TTS
    participant Speaker

    Mic->>Wake: audio-start + audio-chunk
    Wake-->>VAD: detection
    VAD->>ASR: audio-start + chunk
    VAD->>ASR: audio-stop
    ASR-->>Intent: transcript
    Intent-->>Handler: intent
    Handler-->>TTS: synthesize
    TTS-->>Speaker: audio-start + chunk + stop
```

---

## 🧠 Notes

- Event streams are **asynchronous** and **bidirectional**
- All diagrams assume persistent socket connections (no HTTP overhead)
- Services must send `describe`/`info` to negotiate capabilities

