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

TEST_TEXT = "test text"
TEST_CONTEXT = {"test": "context"}
TEST_AUDIO_SETTINGS = {"rate": 22050, "width": 2, "channels": 1}
TEST_ID = "test-id"

TEST_DATA: Dict[str, Dict[str, Any]] = {
    "AudioStart": TEST_AUDIO_SETTINGS,
    "AudioChunk": {**TEST_AUDIO_SETTINGS, "audio": bytes(100)},
    "Error": {"text": TEST_TEXT},
    "Handled": {
        "text": TEST_TEXT,
        "context": TEST_CONTEXT,
    },
    "HandledChunk": {"text": TEST_TEXT},
    "Intent": {"name": "TestIntent", "entities": [Entity("test entity", "test-value")]},
    "MediaPlay": {"url": "test://url"},
    "Recognize": {"text": TEST_TEXT},
    "RunPipeline": {"start_stage": PipelineStage.ASR, "end_stage": PipelineStage.TTS},
    "Synthesize": {"text": TEST_TEXT},
    "SynthesizeChunk": {"text": TEST_TEXT},
    "TimerStarted": {"id": TEST_ID, "total_seconds": 100},
    "TimerUpdated": {"id": TEST_ID, "total_seconds": 100, "is_active": True},
    "TimerFinished": {"id": TEST_ID},
    "TimerCancelled": {"id": TEST_ID},
    "Transcript": {"text": TEST_TEXT},
}


@pytest.mark.parametrize("cls", EVENTABLE_CLASSES)
def test_eventable_round_trip(cls: Type[Eventable]) -> None:
    init_kwargs = TEST_DATA.get(cls.__name__, {})
    instance = cls(**init_kwargs)

    # Test event() method
    event = instance.event()
    assert event.type is not None, f"{cls} returned event with no type"

    # Test is_type matches event.type
    assert cls.is_type(event.type), f"{cls}.is_type failed for {event.type}"

    # Test from_event returns an equivalent object
    round_trip = cls.from_event(event)
    assert round_trip == instance, f"{cls}.from_event failed to round-trip {instance}"
