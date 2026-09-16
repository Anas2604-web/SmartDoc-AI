from collections import Counter
from io import BytesIO
import math
import re
from typing import List

from openai import OpenAI
from pypdf import PdfReader

from app.config import settings
from app.schemas import SourceChunk


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)


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


def _tokens(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(text)]


def _tf_idf_vector(tokens: List[str], document_frequency: Counter, document_count: int) -> dict[str, float]:
    counts = Counter(tokens)
    if not counts:
        return {}
    vector = {
        term: (1.0 + math.log(count)) * (1.0 + math.log((1.0 + document_count) / (1.0 + document_frequency[term])))
        for term, count in counts.items()
    }
    norm = math.sqrt(sum(value * value for value in vector.values()))
    return {term: value / norm for term, value in vector.items()} if norm else {}


def encode_chunks(chunks: List[str]) -> List[dict[str, float]]:
    """Create compact sparse TF-IDF vectors without a model or native ML runtime."""
    token_lists = [_tokens(chunk) for chunk in chunks]
    document_frequency: Counter = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))
    return [
        _tf_idf_vector(tokens, document_frequency, len(chunks))
        for tokens in token_lists
    ]


def create_faiss_index(embeddings: List[dict[str, float]]) -> bytes:
    """Keep the historical storage contract; retrieval is recomputed from chunks."""
    return b"smartdoc-lexical-v1"


def search_chunks(question: str, chunks: List[str], faiss_index_blob: bytes, top_k: int) -> List[SourceChunk]:
    del faiss_index_blob  # Kept in the signature for database and API compatibility.
    if not chunks:
        return []

    token_lists = [_tokens(chunk) for chunk in chunks]
    document_frequency: Counter = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))
    query_vector = _tf_idf_vector(_tokens(question), document_frequency, len(chunks))

    scored = []
    for index, tokens in enumerate(token_lists):
        vector = _tf_idf_vector(tokens, document_frequency, len(chunks))
        score = sum(query_vector.get(term, 0.0) * value for term, value in vector.items())
        scored.append((score, index))

    scored.sort(key=lambda item: (-item[0], item[1]))
    results: List[SourceChunk] = []
    for rank, (score, chunk_index) in enumerate(scored[: min(top_k, len(chunks))], start=1):
        results.append(
            SourceChunk(
                rank=rank,
                score=float(score),
                content=chunks[chunk_index],
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
