from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AIResult:
    moderation_score: float
    fake_score: float
    trust_score: float
    sentiment: str
    category: str
    title: str
    summary: str


class AIModuleService:
    def analyze(self, text: str) -> AIResult:
        lowered = text.lower()
        moderation_score = 0.9 if any(token in lowered for token in {"spam", "scam"}) else 0.1
        fake_score = 0.85 if "breaking" in lowered and "!!!" in text else 0.2
        trust_score = max(0.0, 1.0 - fake_score)
        sentiment = "positive" if any(token in lowered for token in {"good", "great", "win"}) else "neutral"
        category = self._categorize(lowered)
        title = self._title(text)
        summary = self._summary(text)
        return AIResult(
            moderation_score=moderation_score,
            fake_score=fake_score,
            trust_score=trust_score,
            sentiment=sentiment,
            category=category,
            title=title,
            summary=summary,
        )

    def _categorize(self, lowered: str) -> str:
        mapping = {
            "crypto": "finance",
            "market": "finance",
            "ai": "technology",
            "sport": "sports",
            "game": "gaming",
            "polit": "politics",
        }
        for token, category in mapping.items():
            if token in lowered:
                return category
        return "general"

    def _title(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(words[:8])

    def _summary(self, text: str) -> str:
        chunks = text.strip().split(".")
        return chunks[0].strip()[:280]
