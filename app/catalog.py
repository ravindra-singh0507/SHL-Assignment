"""Load and manage SHL product catalog."""

import json
from pathlib import Path
from typing import Optional


class Assessment:
    def __init__(self, data: dict):
        self.entity_id = data.get("entity_id")
        self.name = data.get("name", "")
        self.url = data.get("link", "")
        self.description = data.get("description", "")
        self.job_levels = data.get("job_levels", [])
        self.languages = data.get("languages", [])
        self.duration = data.get("duration", "")
        self.keys = data.get("keys", [])
        self.adaptive = data.get("adaptive", "no")
        self.remote = data.get("remote", "yes")
        self.status = data.get("status", "")

    @property
    def test_type(self) -> str:
        """Map keys array to single test type letter code."""
        key_to_code = {
            "Knowledge & Skills": "K",
            "Personality & Behavior": "P",
            "Ability & Aptitude": "A",
            "Simulations": "S",
            "Biodata & Situational Judgment": "B",
            "Competencies": "C",
            "Development & 360": "D",
        }
        codes = [key_to_code.get(key, "") for key in self.keys if key in key_to_code]
        return ",".join(codes) if codes else ""

    @property
    def searchable_text(self) -> str:
        """Create combined searchable text for embeddings."""
        parts = [
            self.name,
            self.description,
            " ".join(self.keys),
            " ".join(self.job_levels),
            " ".join(self.languages),
        ]
        if self.duration:
            parts.append(self.duration)
        return " ".join(p for p in parts if p).lower()

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "url": self.url,
            "test_type": self.test_type,
        }


class Catalog:
    def __init__(self, catalog_path: str):
        self.assessments: dict[str, Assessment] = {}
        self.load(catalog_path)

    def load(self, catalog_path: str):
        """Load catalog from JSON file."""
        path = Path(catalog_path)
        if not path.exists():
            raise FileNotFoundError(f"Catalog not found at {catalog_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            assessment = Assessment(item)
            # Use entity_id or name as key
            key = assessment.entity_id or assessment.name
            self.assessments[key] = assessment

    def get_by_name(self, name: str) -> Optional[Assessment]:
        """Get assessment by exact name match."""
        for assessment in self.assessments.values():
            if assessment.name.lower() == name.lower():
                return assessment
        return None

    def get_by_id(self, entity_id: str) -> Optional[Assessment]:
        """Get assessment by entity ID."""
        return self.assessments.get(entity_id)

    def get_all(self) -> list[Assessment]:
        """Get all assessments."""
        return list(self.assessments.values())

    def size(self) -> int:
        """Get number of assessments in catalog."""
        return len(self.assessments)
