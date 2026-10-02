# 📦 Wyoming Event Format

Wyoming is a streaming peer-to-peer protocol using newline-delimited JSON (JSONL) plus optional binary data.

It is designed to be:

- 🧩 Simple to implement
- 🔄 Streaming-friendly (audio chunking)
- 🔐 Language-agnostic and open

---

## 🔠 Message Structure

Each Wyoming message is made of:

```
{ "type": "...", "data_length": ..., "payload_length": ... }\n
<data_length bytes>       (optional, UTF-8 JSON)
<payload_length bytes>    (optional, binary payload)
```

- **Header** (required): JSON object, UTF-8, newline terminated
- **Data section** (optional): UTF-8 JSON
- **Payload** (optional): binary blob (e.g., PCM audio)

---

### 🧪 Minimal Example (Audio Chunk)

```json
{ "type": "audio-chunk", "data_length": 0, "payload_length": 3200 }
```

Followed by 3200 bytes of raw PCM audio.

---

### 🔄 With Additional Metadata

```json
{ "type": "transcribe", "data_length": 45, "payload_length": 0 }
```

Followed by:

```json
{ "name": "whisper", "language": "en" }
```

No binary payload in this case.

---

## 🧰 Python Example: Creating an Event

```python
from wyoming.event import Event

event = Event(
    type="synthesize",
    data={"text": "Hello world"},
    payload=b""
)

raw_bytes = event.to_bytes()
```

---

## 🧰 Python Example: Reading an Event from a Stream

```python
from wyoming.event import read_event

async def handle(reader):
    event = await read_event(reader)
    print(event.type, event.data)
```

---

## 🧪 CLI Test (Netcat)

To verify a Wyoming-compatible server is running:

```bash
echo '{"type":"describe"}' | nc localhost 10200
```

Expect response like:

```json
{ "type": "info", ... }
```

---

## 🌐 Format Summary

| Component       | Description                             |
|----------------|-----------------------------------------|
| `type`          | Event type string (e.g. `transcribe`)   |
| `data_length`   | Length of optional JSON block in bytes  |
| `payload_length`| Length of optional binary in bytes      |

Wyoming works over:
- TCP (`tcp://host:port`)
- Unix sockets (`unix:///path`)
- Standard I/O (`stdio://`)

