# 🧪 Section 07 – Example Projects & Clients

This section demonstrates how to build simple Wyoming clients and services for testing and experimentation.

---

## 🎙️ ASR Client (Microphone to Transcript)

Live microphone capture streamed to a Wyoming ASR server.

```python
import sounddevice as sd
from wyoming.client import AsyncClient
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.event import Event
import asyncio

RATE = 16000
CHANNELS = 1
WIDTH = 2

async def stream_mic():
    async with AsyncClient.from_uri("tcp://localhost:10200") as client:
        await client.write_event(AudioStart(rate=RATE, width=WIDTH, channels=CHANNELS).event())

        def callback(indata, frames, time, status):
            chunk = AudioChunk(audio=indata.tobytes(), rate=RATE, width=WIDTH, channels=CHANNELS)
            asyncio.create_task(client.write_event(chunk.event()))

        with sd.InputStream(callback=callback, channels=CHANNELS, samplerate=RATE):
            await asyncio.sleep(5)  # Record for 5 seconds

        await client.write_event(AudioStop().event())
        response = await client.read_event()
        print("Transcription:", response.data["text"])

asyncio.run(stream_mic())
```

---

## 🗣️ TTS Client (Text to WAV)

Send text to a TTS Wyoming server and save audio.

```python
import wave
from wyoming.client import AsyncClient
from wyoming.tts import Synthesize
from wyoming.audio import AudioChunk
from wyoming.event import Event
import asyncio

async def tts_to_wav():
    async with AsyncClient.from_uri("tcp://localhost:10200") as client:
        await client.write_event(Synthesize(text="Hello world").event())

        wav = wave.open("output.wav", "wb")
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)

        while True:
            event = await client.read_event()
            if event.type == "audio-stop":
                break
            if event.type == "audio-chunk":
                chunk = AudioChunk.from_event(event)
                wav.writeframes(chunk.audio)

        wav.close()

asyncio.run(tts_to_wav())
```

---

## 🧠 Intent Recognition

```python
from wyoming.client import AsyncClient
from wyoming.intent import Recognize
from wyoming.event import Event
import asyncio

async def recognize_intent(text):
    async with AsyncClient.from_uri("tcp://localhost:10200") as client:
        await client.write_event(Recognize(text=text).event())
        response = await client.read_event()
        print("Intent:", response.data)

asyncio.run(recognize_intent("Turn off the kitchen light"))
```

---

## 🔁 Echo Test Server

```python
from wyoming.server import serve_forever, AsyncEventHandler
from wyoming.event import Event

class EchoHandler(AsyncEventHandler):
    async def handle_event(self, event):
        return Event(type="echo", data={"echoed": event.type})

await serve_forever("tcp://0.0.0.0:12345", EchoHandler())
```

---

## 🔗 Useful Repositories

- [wyoming-satellite](https://github.com/rhasspy/wyoming-satellite)
- [wyoming-piper](https://github.com/rhasspy/wyoming-piper)
- [wyoming-faster-whisper](https://github.com/rhasspy/wyoming-faster-whisper)
- [wyoming-openwakeword](https://github.com/rhasspy/wyoming-openwakeword)

