# 🤝 Contributing to Wyoming

We welcome contributions from the community to improve Wyoming and its ecosystem.

## 🧱 What Can You Contribute?

- 📚 Documentation improvements
- 🐛 Bug fixes
- ✨ New features or event types
- 🔌 Third-party Wyoming services (ASR, TTS, Wakeword, etc.)
- 🧪 Examples and test clients

## 📦 Code Style

- Python code should follow **PEP8** and use **type annotations**.
- All protocol events should use **dataclasses** with `.event()` and `.from_event()` methods.
- Write **async-first** code when implementing servers or clients.

## 📁 Project Layout

```
wyoming/
├── audio/          # Audio events (PCM stream)
├── asr/            # Speech recognition events
├── tts/            # Text to speech events
├── intent/         # Intent recognition events
├── timer/          # Timer messages
├── handle/         # Intent handling responses
├── server/         # AsyncEventHandler + serve_forever
├── client/         # Async Wyoming client
├── http/           # Optional HTTP servers
```

## 🚦 Running Tests

```bash
pytest
```

## 🧪 Testing Locally

Use `wyoming/server.py` and `client.py` to spin up local services and test interaction manually.

## 🛠️ Submitting a PR

1. Fork the repository
2. Create a feature branch
3. Submit your pull request with a clear description
4. Include tests for new features where possible

## 💬 Communication

Please open an issue for questions, ideas or feature requests.

Thanks for being part of the Wyoming ecosystem!
