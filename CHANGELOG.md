# Changelog

## 1.6.1

- Migrate to pyproject.toml
- Add `language` to `transcript`

## 1.6.0

- Update `run-pipeline` to be bi-directional
    - Add `wake_word_name`
    - Add `wake_word_names`
    - Add `announce_text`
    - Remove `snd_format`
- Update satellite info
    - Add `has_vad`
    - Add `active_wake_words`
    - Add `max_active_wake_words`
    - Add `supports_trigger`
    - Remove `snd_format`
- Add `mic` and `snd` to `info` message
- Update wake word satellite
    - Support remote pipeline triggering
    - Support local VAD

## 1.5.4

- Add support for voice timers
    - `timer-started`
    - `timer-updated`
    - `timer-cancelled`
    - `timer-finished`
- Add `speaker` field to `detect` event
- Refactor HTTP servers

## 1.5.3

- Add `phrase` to wake word model info
- Add tests to CI

## 1.5.2

- Fix missing VERSION file

## 1.5.1

- Add `version` to info artifacts
- Use Python package version in Wyoming JSON header
- Add `pause-satellite` message

## 1.5.0

- Add `ping` and `pong` messages
- Add `satellite-connected` and `satellite-disconnected` messages

## 1.4.2

- Add `streaming-started` and `streaming-stopped`

## 1.3.0

- Add `intent` and `satellite` to info message
- Add optional `text` response to `Intent` message
- Add `context` to intent/handle events
- Use internal `audioop` replacement
- Add zeroconf discovery
