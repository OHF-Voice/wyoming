"""Test that eventable classes are correct."""

import importlib
import inspect
import pkgutil
from typing import Any, Dict, List, Type

import pytest

import wyoming
from wyoming.event import Eventable
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

TEST_NAME = "test-name"
TEST_TEXT = "test text"
TEST_CONTEXT = {"test": "context"}
TEST_AUDIO_SETTINGS = {"rate": 22050, "width": 2, "channels": 1}
TEST_ID = "test-id"
TEST_LANGUAGE = "test-language"
TEST_SPEAKER = "test-speaker"
TEST_TIMESTAMP = 1234
TEST_VOICE = SynthesizeVoice(name=TEST_NAME, speaker=TEST_SPEAKER)

TEST_DATA: Dict[str, Dict[str, Any]] = {
    # info
    "Describe": {},
    "Info": {},
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
    # media
    "MediaPlay": {"url": "test://url"},
    "MediaStop": {},
    "MediaPause": {},
    "MediaUnpause": {},
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
