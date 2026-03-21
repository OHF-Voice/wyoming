"""Tests for pipeline stage validation."""

import pytest

from wyoming.pipeline import PipelineStage, RunPipeline


def test_pipeline_identity_stage_valid() -> None:
    """Identity stage is a peer of ASR before text stages."""
    RunPipeline(start_stage=PipelineStage.WAKE, end_stage=PipelineStage.IDENTITY)
    RunPipeline(start_stage=PipelineStage.IDENTITY, end_stage=PipelineStage.ASR)
    RunPipeline(start_stage=PipelineStage.ASR, end_stage=PipelineStage.IDENTITY)
    RunPipeline(start_stage=PipelineStage.IDENTITY, end_stage=PipelineStage.TTS)


def test_pipeline_identity_stage_invalid() -> None:
    """Identity stage cannot come after text stages."""
    with pytest.raises(ValueError):
        RunPipeline(start_stage=PipelineStage.INTENT, end_stage=PipelineStage.IDENTITY)


def test_pipeline_identity_result_round_trip() -> None:
    """Recognized identity is preserved in pipeline state."""
    pipeline = RunPipeline(
        start_stage=PipelineStage.ASR,
        end_stage=PipelineStage.TTS,
        identity_name="test-identity",
    )
    assert RunPipeline.from_event(pipeline.event()) == pipeline
