from wyoming.event import Event
from wyoming.tts import (
    Synthesize,
    SynthesizeStart,
    SynthesizeTextFormat,
    SynthesizeVoice,
)


def test_voice_preserves_language_with_name_and_speaker() -> None:
    voice = SynthesizeVoice(name="voice", language="en-US", speaker="speaker")

    assert voice.to_dict() == {
        "name": "voice",
        "language": "en-US",
        "speaker": "speaker",
    }
    assert SynthesizeVoice.from_dict(voice.to_dict()) == voice



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
