# 🐍 Wyoming Python Modules

This section documents the Python modules exposed by Wyoming and how to use them to build your own services or clients.

---

## 🧩 `wyoming.event`

### `Event`
Represents a Wyoming message.

```python
from wyoming.event import Event

event = Event(type="ping", data={"hello": "world"})
raw = event.to_bytes()
```

### `read_event` / `write_event`
Async functions to read/write Wyoming messages.

```python
from wyoming.event import read_event, write_event

event = await read_event(reader)
await write_event(writer, event)
```

---

## 🧑‍💻 `wyoming.client`

### `AsyncClient`
Creates a client that connects via TCP, Unix socket, or stdio.

```python
from wyoming.client import AsyncClient

async with AsyncClient.from_uri("tcp://localhost:10200") as client:
    await client.write_event(Event(type="ping"))
    response = await client.read_event()
    print(response.type)
```

---

## 🖧 `wyoming.server`

### `AsyncEventHandler`
Base class for implementing servers.

```python
from wyoming.server import AsyncEventHandler

class MyHandler(AsyncEventHandler):
    async def handle_event(self, event):
        if event.type == "ping":
            return Event(type="pong")
```

### `serve_forever`
Starts a Wyoming-compatible server.

```python
from wyoming.server import serve_forever

await serve_forever("tcp://0.0.0.0:1234", MyHandler())
```

---

## 🔊 `wyoming.audio`

### `AudioStart`, `AudioChunk`, `AudioStop`

```python
from wyoming.audio import AudioStart, AudioChunk, AudioStop

start = AudioStart(rate=16000, width=2, channels=1)
chunk = AudioChunk(audio=b"...")
stop = AudioStop()

event = chunk.event()
```

---

## 🧠 `wyoming.asr`

```python
from wyoming.asr import Transcribe, Transcript

request = Transcribe(name="whisper", language="en")
response = Transcript(text="hello world", confidence=0.98)
```

---

## 🗣️ `wyoming.tts`

```python
from wyoming.tts import Synthesize

synth = Synthesize(text="Hi there!", voice={"language": "en"})
```

---

## 🤖 `wyoming.intent`

```python
from wyoming.intent import Recognize, Intent, NotRecognized

recognize = Recognize(text="Turn off the lights")
```

---

## 🛠️ `wyoming.handle`

```python
from wyoming.handle import Handled, NotHandled

ok = Handled(text="OK, turning off lights")
fail = NotHandled(text="I don't know how to do that")
```

---

## ⏰ `wyoming.timer`

```python
from wyoming.timer import TimerStarted

ts = TimerStarted(id="t1", total_seconds=60)
```

---

## 🧪 Utilities

### `wyoming.util.dataclasses_json`

JSON-to-dataclass helpers (internal)

### `wyoming.zeroconf`

mDNS service publishing for discovery

---

## 🌐 HTTP Servers

- `wyoming.http.asr_server`: WAV to text
- `wyoming.http.tts_server`: text to audio
- `wyoming.http.intent_server`: text to intent

Use Flask + Wyoming backend.

---

## 🔧 Example: Custom Wyoming Echo Server

```python
from wyoming.server import serve_forever, AsyncEventHandler
from wyoming.event import Event

class EchoHandler(AsyncEventHandler):
    async def handle_event(self, event):
        return Event(type="echo", data={"you_sent": event.type})

await serve_forever("tcp://0.0.0.0:12345", EchoHandler())
```

Connect via netcat:

```bash
echo '{"type":"hello"}' | nc localhost 12345
```

---

## 🧠 Best Practices

- Use `.event()` to serialize any domain class
- Use `.from_event(event)` to deserialize
- Prefer `AsyncClient.from_uri(...)` for universal compatibility
- Write robust handlers that respond to `describe`, `ping`, `transcribe`, etc.

