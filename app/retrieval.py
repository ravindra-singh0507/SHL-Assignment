"""Vector search using TF-IDF and cosine similarity (lightweight for deployment)."""

import pickle
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .catalog import Catalog, Assessment


class Retrieval:
    def __init__(
        self,
        catalog: Catalog,
        index_path: str = "vector_store/tfidf_index.pkl",
    ):
        self.catalog = catalog
        self.index_path = Path(index_path)
        self.vectorizer = None
        self.tfidf_matrix = None
        self.assessment_ids = []
        self.assessment_map = {}

    def build_index(self):
        """Build TF-IDF index from catalog."""
        assessments = self.catalog.get_all()
        if not assessments:
            raise ValueError("No assessments in catalog to index")

        texts = [a.searchable_text for a in assessments]

        # Build TF-IDF matrix
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

        # Store metadata
        self.assessment_ids = [a.entity_id or a.name for a in assessments]
        self.assessment_map = {
            aid: self.catalog.assessments[aid] for aid in self.assessment_ids
        }

    def save_index(self):
        """Save TF-IDF index to disk."""
        if self.vectorizer is None:
            raise ValueError("Index not built yet")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self.vectorizer,
                    "tfidf_matrix": self.tfidf_matrix,
                    "assessment_ids": self.assessment_ids,
                    "assessment_map": self.assessment_map,
                },
                f,
            )

    def load_index(self):
        """Load TF-IDF index from disk."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index not found at {self.index_path}")
        with open(self.index_path, "rb") as f:
            data = pickle.load(f)
            self.vectorizer = data["vectorizer"]
            self.tfidf_matrix = data["tfidf_matrix"]
            self.assessment_ids = data["assessment_ids"]
            self.assessment_map = data["assessment_map"]

    def search(self, query: str, k: int = 5) -> list[Assessment]:
        """Search for similar assessments using cosine similarity."""
        if self.vectorizer is None:
            raise ValueError("Index not loaded or built")

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero matches
                aid = self.assessment_ids[idx]
                assessment = self.assessment_map.get(aid)
                if assessment:
                    results.append(assessment)
        return results

    def search_by_names(self, names: list[str]) -> list[Assessment]:
        """Search for assessments by exact name match."""
        results = []
        for name in names:
            assessment = self.catalog.get_by_name(name)
            if assessment:
                results.append(assessment)
        return results
