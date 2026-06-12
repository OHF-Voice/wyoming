from wyoming.event import Event
from wyoming.tts import Synthesize, SynthesizeStart, SynthesizeTextFormat


def test_text_format() -> None:
    assert Synthesize.from_event(
        Event("synthesize", {"text": "test text", "text_format": "ssml"})
    ) == Synthesize("test text", text_format=SynthesizeTextFormat.SSML)

    assert Synthesize.from_event(
        Event("synthesize", {"text": "test text", "text_format": "other-format"})
    ) == Synthesize("test text", text_format="other-format")

    assert SynthesizeStart.from_event(
        Event("synthesize", {"text_format": "ssml"})
    ) == SynthesizeStart(text_format=SynthesizeTextFormat.SSML)

    assert SynthesizeStart.from_event(
        Event("synthesize", {"text_format": "other-format"})
    ) == SynthesizeStart(text_format="other-format")
