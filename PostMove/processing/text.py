from __future__ import annotations

from dataclasses import dataclass

from PostMove.settings.models import ProcessingSettings


@dataclass(slots=True)
class TextProcessResult:
    text: str
    denied: bool


class TextProcessor:
    def __init__(self, settings: ProcessingSettings) -> None:
        self._settings = settings

    def reload(self, settings: ProcessingSettings) -> None:
        self._settings = settings

    def process(self, text: str | None) -> TextProcessResult:
        content = (text or "").strip()
        for marker in self._settings.source_markers:
            content = content.replace(marker, "")

        lowered = content.lower()
        if any(word.lower() in lowered for word in self._settings.deny_words):
            return TextProcessResult(text=content, denied=True)

        for old, new in self._settings.replacers.items():
            content = content.replace(old, new)

        if self._settings.auto_bold_title and content:
            lines = content.splitlines()
            lines[0] = f"**{lines[0].strip()}**"
            content = "\\n".join(lines)

        return TextProcessResult(text=content, denied=False)
