from __future__ import annotations

from dataclasses import dataclass

from PostMove.processing.text import TextProcessor
from PostMove.settings.models import ProcessingSettings


@dataclass(slots=True)
class ProcessedContent:
    text: str
    denied: bool
    buttons: list[dict[str, str]]


class ContentProcessor:
    def __init__(self, settings: ProcessingSettings) -> None:
        self._settings = settings
        self._text = TextProcessor(settings)

    def reload(self, settings: ProcessingSettings) -> None:
        self._settings = settings
        self._text.reload(settings)

    def process(self, text: str | None) -> ProcessedContent:
        result = self._text.process(text)
        return ProcessedContent(
            text=result.text,
            denied=result.denied,
            buttons=[button.model_dump() for button in self._settings.default_buttons],
        )
