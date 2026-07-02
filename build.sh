#!/bin/bash
pip install -r requirements.txt

# Pre-download the sentence-transformers model during build
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
