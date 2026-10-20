import uuid
from typing import Any, Dict, List, Set

from mock_data.loader import get_moderation_data


class ModerationEngine:
    """Manages sensitive keyword dictionaries loaded from independent mock_data."""

    def __init__(self):
        initial_keywords = get_moderation_data().get("keywords", [])
        self._keywords: Set[str] = set(initial_keywords)

    def list_keywords(self) -> List[str]:
        return sorted(list(self._keywords))

    def add_keyword(self, word: str) -> bool:
        w = word.strip()
        if not w:
            return False
        self._keywords.add(w)
        return True

    def remove_keyword(self, word: str) -> bool:
        w = word.strip()
        if w in self._keywords:
            self._keywords.remove(w)
            return True
        return False

    def reset_keywords(self) -> List[str]:
        base_keywords = get_moderation_data().get("keywords", [])
        self._keywords = set(base_keywords)
        return self.list_keywords()

    def scan_content(self, content: str) -> Dict[str, Any]:
        """Scans text against current keyword rules and outputs Aliyun Green compatible result."""
        hit_words = [kw for kw in self._keywords if kw in content]
        
        if hit_words:
            return {
                "suggestion": "block",
                "label": "contraband",
                "rate": 99.0,
                "hit_words": hit_words,
                "filtered_content": self._mask_content(content, hit_words),
            }
        
        return {
            "suggestion": "pass",
            "label": "normal",
            "rate": 0.0,
            "hit_words": [],
            "filtered_content": content,
        }

    def _mask_content(self, content: str, hit_words: List[str]) -> str:
        masked = content
        for kw in hit_words:
            masked = masked.replace(kw, "*" * len(kw))
        return masked


moderation_engine = ModerationEngine()
