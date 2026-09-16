from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import fetch_document, fetch_insights, init_db, log_question, store_document
from app.rag import chunk_text, create_faiss_index, encode_chunks, extract_text_from_pdf, generate_answer, search_chunks
from app.schemas import AskRequest, AskResponse, InsightsResponse, UploadResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
    except Exception:
        # A transient database issue must not prevent health checks or the
        # frontend from loading during a serverless cold start.
        logger.exception("Database initialization failed; database-backed actions may be unavailable.")
    yield


app = FastAPI(title="SmartDoc AI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def healthcheck():
    return {
        "status": "ok",
        "postgres_configured": bool(settings.postgres_url),
        "answer_provider": "groq" if settings.groq_api_key else "deepseek" if settings.deepseek_api_key else None,
        "answer_api_configured": bool(settings.answer_api_key),
    }


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

    try:
        text = extract_text_from_pdf(file_bytes)
        chunks = chunk_text(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to process the PDF.") from exc

    if not chunks:
        raise HTTPException(status_code=400, detail="No text chunks were created from the PDF.")

    try:
        embeddings = encode_chunks(chunks)
        index_blob = create_faiss_index(embeddings)
        document_id = str(uuid4())
        store_document(document_id=document_id, pdf_name=filename, chunks=chunks, faiss_index=index_blob)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to store the processed document.") from exc

    return UploadResponse(
        document_id=document_id,
        pdf_name=filename,
        chunk_count=len(chunks),
    )


@app.post("/api/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest):
    document = fetch_document(payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found. Upload the PDF again.")

    chunks = document["chunks"]
    pdf_name = document["pdf_name"]
    faiss_index_blob = document["faiss_index"]

    try:
        sources = search_chunks(
            question=payload.question,
            chunks=chunks,
            faiss_index_blob=faiss_index_blob,
            top_k=settings.top_k,
        )
        answer = generate_answer(payload.question, sources)
        log_question(payload.question, pdf_name, len(answer))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to answer the question.") from exc

    return AskResponse(
        answer=answer,
        sources=sources,
        pdf_name=pdf_name,
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/api/insights", response_model=InsightsResponse)
async def insights():
    try:
        data = fetch_insights()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load insights.") from exc

    return InsightsResponse(**data)
