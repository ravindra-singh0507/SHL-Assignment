"""Vector search using FAISS and sentence transformers."""

import pickle
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from .catalog import Catalog, Assessment


class Retrieval:
    def __init__(
        self,
        catalog: Catalog,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: str = "vector_store/faiss_index.pkl",
    ):
        self.catalog = catalog
        self.model = SentenceTransformer(model_name)
        self.index_path = Path(index_path)
        self.index = None
        self.assessment_ids = []
        self.assessment_map = {}

    def build_index(self):
        """Build FAISS index from catalog."""
        assessments = self.catalog.get_all()
        if not assessments:
            raise ValueError("No assessments in catalog to index")

        # Generate embeddings
        texts = [a.searchable_text for a in assessments]
        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings).astype("float32")

        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        # Store metadata
        self.assessment_ids = [a.entity_id or a.name for a in assessments]
        self.assessment_map = {
            aid: self.catalog.assessments[aid] for aid in self.assessment_ids
        }

    def save_index(self):
        """Save FAISS index to disk."""
        if self.index is None:
            raise ValueError("Index not built yet")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "wb") as f:
            pickle.dump(
                {
                    "index": self.index,
                    "assessment_ids": self.assessment_ids,
                    "assessment_map": self.assessment_map,
                },
                f,
            )

    def load_index(self):
        """Load FAISS index from disk."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index not found at {self.index_path}")
        with open(self.index_path, "rb") as f:
            data = pickle.load(f)
            self.index = data["index"]
            self.assessment_ids = data["assessment_ids"]
            self.assessment_map = data["assessment_map"]

    def search(self, query: str, k: int = 5) -> list[Assessment]:
        """Search for similar assessments."""
        if self.index is None:
            raise ValueError("Index not loaded or built")

        query_embedding = self.model.encode([query])[0]
        query_embedding = np.array([query_embedding]).astype("float32")

        distances, indices = self.index.search(query_embedding, k)
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.assessment_ids):
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
