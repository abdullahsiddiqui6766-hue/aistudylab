"""
services/vector_store.py

Thin wrapper around a local ChromaDB persistent client. Each uploaded PDF
gets its own collection, named after the content hash of the file, so that
re-uploading the same PDF in a later session reuses existing embeddings
instead of recomputing them (Requirement: avoid reprocessing the same PDF).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st

from services.embeddings import embed_texts, embed_query
from services.pdf_processor import Chunk

CHROMA_DIR = ".chroma_store"


@st.cache_resource(show_spinner=False)
def get_chroma_client():
    import chromadb

    return chromadb.PersistentClient(path=CHROMA_DIR)


def collection_name(pdf_hash: str) -> str:
    return f"studyai_{pdf_hash}"


def collection_exists(pdf_hash: str) -> bool:
    client = get_chroma_client()
    try:
        names = [c.name for c in client.list_collections()]
    except Exception:
        names = []
    return collection_name(pdf_hash) in names


def build_collection(pdf_hash: str, chunks: List[Chunk]) -> None:
    """Embeds and stores all chunks for a PDF. No-op if already built."""
    client = get_chroma_client()
    name = collection_name(pdf_hash)

    # Fresh start if it already exists (e.g. user re-uploaded a changed file
    # with a colliding partial state) to keep things consistent.
    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(name=name)

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)

    ids = [c.chunk_id for c in chunks]
    metadatas = [
        {
            "page": c.page if c.page is not None else -1,
            "chapter": c.chapter or "",
        }
        for c in chunks
    ]

    batch = 200
    for i in range(0, len(chunks), batch):
        collection.add(
            ids=ids[i : i + batch],
            embeddings=vectors[i : i + batch],
            documents=texts[i : i + batch],
            metadatas=metadatas[i : i + batch],
        )


def query(
    pdf_hash: str,
    question: str,
    top_k: int = 6,
    chapter_filter: Optional[str] = None,
) -> List[Dict]:
    client = get_chroma_client()
    try:
        collection = client.get_collection(collection_name(pdf_hash))
    except Exception:
        return []

    query_vector = embed_query(question)
    where = {"chapter": chapter_filter} if chapter_filter else None

    result = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where=where,
    )

    hits = []
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0] if result.get("distances") else [None] * len(docs)

    for doc, meta, dist in zip(docs, metas, dists):
        hits.append(
            {
                "text": doc,
                "page": meta.get("page") if meta.get("page", -1) != -1 else None,
                "chapter": meta.get("chapter") or None,
                "distance": dist,
            }
        )
    return hits


def get_all_chunks_for_chapter(pdf_hash: str, chapter: Optional[str], limit: int = 40) -> List[Dict]:
    """Pulls chunks belonging to a specific chapter directly (not via
    similarity search) -- used for MCQ / question generation where we want
    broad chapter coverage rather than query-relevance."""
    client = get_chroma_client()
    try:
        collection = client.get_collection(collection_name(pdf_hash))
    except Exception:
        return []

    where = {"chapter": chapter} if chapter else None
    result = collection.get(where=where, limit=limit)

    hits = []
    docs = result.get("documents", [])
    metas = result.get("metadatas", [])
    for doc, meta in zip(docs, metas):
        hits.append(
            {
                "text": doc,
                "page": meta.get("page") if meta.get("page", -1) != -1 else None,
                "chapter": meta.get("chapter") or None,
            }
        )
    return hits
