"""
services/embeddings.py

Local, free embeddings via sentence-transformers (all-MiniLM-L6-v2).
The model is loaded once per server process using st.cache_resource so it is
not reloaded on every Streamlit rerun.
"""

from __future__ import annotations

from typing import List

import streamlit as st

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


@st.cache_resource(show_spinner=False)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
        batch_size=32,
    )
    return vectors.tolist()


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]
