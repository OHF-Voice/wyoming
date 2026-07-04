"""Pipeline events."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .event import Event, Eventable

_RUN_PIPELINE_TYPE = "run-pipeline"


class PipelineStage(str, Enum):
    """Stages of a pipeline."""

    WAKE = "wake"
    """Wake word detection."""

    ASR = "asr"
    """Speech-to-text (a.k.a. automated speech recognition)."""

    INTENT = "intent"
    """Intent recognition."""

    HANDLE = "handle"
    """Intent handling."""

    TTS = "tts"
    """Text-to-speech."""


@dataclass
class RunPipeline(Eventable):
    """Run a pipeline"""

    start_stage: PipelineStage
    """Stage to start the pipeline on."""

    end_stage: PipelineStage
    """Stage to end the pipeline on."""

    wake_word_name: Optional[str] = None
    """Name of wake word that triggered this pipeline."""

    restart_on_end: bool = False
    """True if pipeline should restart automatically after ending."""

    wake_word_names: Optional[List[str]] = None
    """Wake word names to listen for (start_stage = wake)."""

    announce_text: Optional[str] = None
    """Text to announce using text-to-speech (start_stage = tts)"""

    def __post_init__(self) -> None:
        start_valid = True
        end_valid = True

        if self.start_stage == PipelineStage.WAKE:
            if self.end_stage not in (
                PipelineStage.WAKE,
                PipelineStage.ASR,
                PipelineStage.INTENT,
                PipelineStage.HANDLE,
                PipelineStage.TTS,
            ):
                end_valid = False
        elif self.start_stage == PipelineStage.ASR:
            if self.end_stage not in (
                PipelineStage.ASR,
                PipelineStage.INTENT,
                PipelineStage.HANDLE,
                PipelineStage.TTS,
            ):
                end_valid = False
        elif self.start_stage == PipelineStage.INTENT:
            if self.end_stage not in (
                PipelineStage.INTENT,
                PipelineStage.HANDLE,
                PipelineStage.TTS,
            ):
                end_valid = False
        elif self.start_stage == PipelineStage.HANDLE:
            if self.end_stage not in (
                PipelineStage.HANDLE,
                PipelineStage.TTS,
            ):
                end_valid = False
        elif self.start_stage == PipelineStage.TTS:
            if self.end_stage not in (PipelineStage.TTS,):
                end_valid = False
        else:
            start_valid = False

        if not start_valid:
            raise ValueError(f"Invalid start stage: {self.start_stage}")

        if not end_valid:
            raise ValueError(f"Invalid end stage: {self.end_stage}")

    @staticmethod
    def is_type(event_type: str) -> bool:
        return event_type == _RUN_PIPELINE_TYPE

    def event(self) -> Event:
        data: Dict[str, Any] = {
            "start_stage": self.start_stage.value,
            "end_stage": self.end_stage.value,
            "restart_on_end": self.restart_on_end,
        }

        if self.wake_word_name is not None:
            data["wake_word_name"] = self.wake_word_name

        if self.wake_word_names:
            data["wake_word_names"] = self.wake_word_names

        if self.announce_text is not None:
            data["announce_text"] = self.announce_text

        return Event(type=_RUN_PIPELINE_TYPE, data=data)

    @staticmethod
    def from_event(event: Event) -> "RunPipeline":
        return RunPipeline(
            start_stage=PipelineStage(event.data["start_stage"]),
            end_stage=PipelineStage(event.data["end_stage"]),
            wake_word_name=event.data.get("wake_word_name"),
            restart_on_end=event.data.get("restart_on_end", False),
            wake_word_names=event.data.get("wake_word_names"),
            announce_text=event.data.get("announce_text"),
        )
