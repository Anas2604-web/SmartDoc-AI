from functools import lru_cache
from io import BytesIO
from typing import List

import faiss
import numpy as np
from openai import OpenAI
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.schemas import SourceChunk


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(page.strip() for page in pages if page.strip())
    if not text:
        raise ValueError("No extractable text was found in the PDF.")
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, 0)
    return chunks


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def encode_chunks(chunks: List[str]) -> np.ndarray:
    model = get_embedding_model()
    embeddings = model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.astype("float32")


def create_faiss_index(embeddings: np.ndarray) -> bytes:
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    return faiss.serialize_index(index).tobytes()


def search_chunks(question: str, chunks: List[str], faiss_index_blob: bytes, top_k: int) -> List[SourceChunk]:
    model = get_embedding_model()
    query_vector = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype("float32")

    index_bytes = np.frombuffer(faiss_index_blob, dtype="uint8").copy()
    index = faiss.deserialize_index(index_bytes)
    scores, indices = index.search(query_vector, min(top_k, len(chunks)))

    results: List[SourceChunk] = []
    for rank, (score, chunk_index) in enumerate(zip(scores[0], indices[0]), start=1):
        if chunk_index < 0:
            continue
        results.append(
            SourceChunk(
                rank=rank,
                score=float(score),
                content=chunks[int(chunk_index)],
            )
        )
    return results


def generate_answer(question: str, sources: List[SourceChunk]) -> str:
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    context = "\n\n".join(
        f"Source {item.rank}:\n{item.content}" for item in sources
    )
    prompt = (
        "Answer only using the provided context. "
        "If the answer is not in the context, say so."
    )

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    response = client.chat.completions.create(
        model=settings.deepseek_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
    )
    return (response.choices[0].message.content or "").strip()
