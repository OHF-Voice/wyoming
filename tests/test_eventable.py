"""Test that eventable classes are correct."""

import importlib
import inspect
import pkgutil
from dataclasses import MISSING, fields
from typing import Any, Dict, List, Type

import pytest

import wyoming
from wyoming.audio import AudioFormat
from wyoming.event import Eventable
from wyoming.info import (
    AsrModel,
    AsrProgram,
    Attribution,
    HandleModel,
    HandleProgram,
    IntentModel,
    IntentProgram,
    MicProgram,
    Satellite,
    SndProgram,
    TtsProgram,
    TtsVoice,
    TtsVoiceSpeaker,
    WakeModel,
    WakeProgram,
)
from wyoming.intent import Entity
from wyoming.pipeline import PipelineStage
from wyoming.tts import SynthesizeVoice


def all_unique_eventables() -> List[Type[Eventable]]:
    found_classes = set()
    for _finder, name, _ispkg in pkgutil.walk_packages(
        wyoming.__path__, wyoming.__name__ + "."
    ):
        module = importlib.import_module(name)
        for _cls_name, cls_obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls_obj, Eventable) and cls_obj is not Eventable:
                found_classes.add(cls_obj)  # set for uniqueness

    return list(found_classes)


EVENTABLE_CLASSES = all_unique_eventables()
NO_ARGS_CLASSES = [
    cls
    for cls in EVENTABLE_CLASSES
    if all(
        f.default is not MISSING or f.default_factory is not MISSING
        for f in fields(cls)  # type: ignore[arg-type]
    )
]

TEST_NAME = "test-name"
TEST_TEXT = "test text"
TEST_CONTEXT = {"test": "context"}
TEST_AUDIO_SETTINGS = {"rate": 22050, "width": 2, "channels": 1}
TEST_AUDIO_FORMAT = AudioFormat(22050, 2, 1)
TEST_ID = "test-id"
TEST_LANGUAGE = "test-language"
TEST_SPEAKER = "test-speaker"
TEST_TIMESTAMP = 1234
TEST_URL = "test://url"
TEST_DESCRIPTION = "test description"
TEST_VERSION = "test-version"
TEST_WAKE_WORD = "test-wake-word"
TEST_VOICE = SynthesizeVoice(name=TEST_NAME, speaker=TEST_SPEAKER)
TEST_ATTRIBUTION = Attribution(name=TEST_NAME, url=TEST_URL)

TEST_DATA: Dict[str, Dict[str, Any]] = {
    # info
    "Describe": {},
    "Info": {
        "asr": [
            AsrProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                models=[
                    AsrModel(
                        name=TEST_NAME,
                        attribution=TEST_ATTRIBUTION,
                        installed=True,
                        description=TEST_DESCRIPTION,
                        version=TEST_VERSION,
                        languages=[TEST_LANGUAGE],
                    )
                ],
                supports_transcript_streaming=True,
            )
        ],
        "tts": [
            TtsProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                voices=[
                    TtsVoice(
                        name=TEST_NAME,
                        attribution=TEST_ATTRIBUTION,
                        installed=True,
                        description=TEST_DESCRIPTION,
                        version=TEST_VERSION,
                        languages=[TEST_LANGUAGE],
                        speakers=[TtsVoiceSpeaker(TEST_SPEAKER)],
                    )
                ],
                supports_synthesize_streaming=True,
            )
        ],
        "handle": [
            HandleProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                models=[
                    HandleModel(
                        name=TEST_NAME,
                        attribution=TEST_ATTRIBUTION,
                        installed=True,
                        description=TEST_DESCRIPTION,
                        version=TEST_VERSION,
                        languages=[TEST_LANGUAGE],
                    )
                ],
                supports_handled_streaming=True,
            )
        ],
        "intent": [
            IntentProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                models=[
                    IntentModel(
                        name=TEST_NAME,
                        attribution=TEST_ATTRIBUTION,
                        installed=True,
                        description=TEST_DESCRIPTION,
                        version=TEST_VERSION,
                        languages=[TEST_LANGUAGE],
                    )
                ],
            )
        ],
        "wake": [
            WakeProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                models=[
                    WakeModel(
                        name=TEST_NAME,
                        attribution=TEST_ATTRIBUTION,
                        installed=True,
                        description=TEST_DESCRIPTION,
                        version=TEST_VERSION,
                        languages=[TEST_LANGUAGE],
                        phrase="test phrase",
                    )
                ],
            )
        ],
        "mic": [
            MicProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                mic_format=TEST_AUDIO_FORMAT,
            )
        ],
        "snd": [
            SndProgram(
                name=TEST_NAME,
                attribution=TEST_ATTRIBUTION,
                installed=True,
                description=TEST_DESCRIPTION,
                version=TEST_VERSION,
                snd_format=TEST_AUDIO_FORMAT,
            )
        ],
        "satellite": Satellite(
            name=TEST_NAME,
            attribution=TEST_ATTRIBUTION,
            installed=True,
            description=TEST_DESCRIPTION,
            version=TEST_VERSION,
            area="test area",
            has_vad=True,
            active_wake_words=[TEST_WAKE_WORD],
            max_active_wake_words=1,
            supports_trigger=True,
        ),
    },
    # audio
    "AudioStart": TEST_AUDIO_SETTINGS,
    "AudioChunk": {**TEST_AUDIO_SETTINGS, "audio": bytes(100)},
    "AudioStop": {},
    # vad
    "VoiceStarted": {"timestamp": TEST_TIMESTAMP},
    "VoiceStopped": {"timestamp": TEST_TIMESTAMP},
    # wake
    "Detect": {"names": [TEST_NAME], "context": TEST_CONTEXT},
    "Detection": {
        "name": TEST_NAME,
        "timestamp": TEST_TIMESTAMP,
        "speaker": TEST_SPEAKER,
        "context": TEST_CONTEXT,
    },
    "NotDetected": {"context": TEST_CONTEXT},
    # asr
    "Transcribe": {
        "name": TEST_NAME,
        "context": TEST_CONTEXT,
        "language": TEST_LANGUAGE,
    },
    "Transcript": {
        "text": TEST_TEXT,
        "context": TEST_CONTEXT,
        "language": TEST_LANGUAGE,
    },
    "TranscriptStart": {
        "context": TEST_CONTEXT,
        "language": TEST_LANGUAGE,
    },
    "TranscriptChunk": {"text": TEST_TEXT},
    "TranscriptStop": {},
    # intent
    "Recognize": {"text": TEST_TEXT, "context": TEST_CONTEXT},
    "Intent": {
        "name": "TestIntent",
        "entities": [Entity("test entity", "test-value")],
        "context": TEST_CONTEXT,
    },
    "NotRecognized": {"text": TEST_TEXT, "context": TEST_CONTEXT},
    # handle
    "Handled": {
        "text": TEST_TEXT,
        "context": TEST_CONTEXT,
    },
    "HandledStart": {"context": TEST_CONTEXT},
    "HandledChunk": {"text": TEST_TEXT},
    "HandledStop": {},
    "NotHandled": {
        "text": TEST_TEXT,
        "context": TEST_CONTEXT,
    },
    # tts
    "SynthesizeStart": {"voice": TEST_VOICE, "context": TEST_CONTEXT},
    "SynthesizeChunk": {"text": TEST_TEXT},
    "SynthesizeStop": {},
    "SynthesizeStopped": {},
    "Synthesize": {"text": TEST_TEXT, "voice": TEST_VOICE, "context": TEST_CONTEXT},
    # timers
    "TimerStarted": {"id": TEST_ID, "total_seconds": 100},
    "TimerUpdated": {"id": TEST_ID, "total_seconds": 100, "is_active": True},
    "TimerFinished": {"id": TEST_ID},
    "TimerCancelled": {"id": TEST_ID},
    # snd
    "Played": {},
    # satellite
    "RunSatellite": {},
    "PauseSatellite": {},
    "StreamingStarted": {},
    "StreamingStopped": {},
    "SatelliteConnected": {},
    "SatelliteDisconnected": {},
    # misc
    "Error": {"text": TEST_TEXT},
    "Ping": {},
    "Pong": {},
    "RunPipeline": {"start_stage": PipelineStage.ASR, "end_stage": PipelineStage.TTS},
}


@pytest.mark.parametrize("cls", EVENTABLE_CLASSES)
def test_eventable_round_trip(cls: Type[Eventable]) -> None:
    init_kwargs = TEST_DATA[cls.__name__]
    instance = cls(**init_kwargs)

    # Test event() method
    event = instance.event()
    assert event.type is not None, f"{cls} returned event with no type"

    # Test is_type matches event.type
    assert cls.is_type(event.type), f"{cls}.is_type failed for {event.type}"

    # Test from_event returns an equivalent object
    round_trip = cls.from_event(event)
    assert round_trip == instance, f"{cls}.from_event failed to round-trip {instance}"


@pytest.mark.parametrize("cls", NO_ARGS_CLASSES)
def test_eventable_no_args(cls: Type[Eventable]) -> None:
    instance = cls()

    # Test event() method
    event = instance.event()
    assert event.type is not None, f"{cls} returned event with no type"

    # Test is_type matches event.type
    assert cls.is_type(event.type), f"{cls}.is_type failed for {event.type}"

    # Test from_event returns an equivalent object
    round_trip = cls.from_event(event)
    assert round_trip == instance, f"{cls}.from_event failed to round-trip {instance}"
