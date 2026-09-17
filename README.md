# SmartDoc AI

SmartDoc AI is a full-stack document Q&A app built with Vue 3, Vite, Tailwind CSS, and FastAPI. It uses Retrieval-Augmented Generation (RAG) to answer questions from uploaded PDFs, stores document chunks in Postgres-backed persistence for Vercel serverless compatibility, and logs query analytics in Vercel Postgres.

## Stack

- Frontend: Vue 3 + Vite + Tailwind CSS
- Backend: FastAPI
- LLM: DeepSeek API through the OpenAI Python SDK
- Retrieval: dependency-free sparse TF-IDF cosine similarity
- Database: Vercel Postgres

The API intentionally avoids PyTorch, sentence-transformers, NumPy, FAISS, and other native ML runtimes. This keeps the Vercel serverless function well below its bundle-size limit while preserving the same upload, retrieval, answer, persistence, and analytics endpoints.

## Project structure

```text
frontend/   Vue 3 client
api/        FastAPI backend
vercel.json Multi-service Vercel config
```

## Features

- Upload a PDF file
- Extract text with `pypdf`
- Split text into ~500-character chunks with 50-character overlap
- Rank chunks with sparse TF-IDF cosine similarity
- Store document chunks and a compact retrieval marker in Postgres
- Retrieve top 3 chunks for each question
- Ask DeepSeek to answer strictly from retrieved context
- Return grounded answers with source chunks
- Log question text, timestamp, PDF name, and answer length
- Show insights for most asked questions, total questions asked, and questions per day

## Environment variables

Set these in Vercel for the `api` service:

- `DEEPSEEK_API_KEY`
- `POSTGRES_URL`

Optional:

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-chat`
- `SMARTDOC_GROQ_API_KEY` (backup)
- `GROQ_BASE_URL=https://api.groq.com/openai/v1`
- `GROQ_MODEL=llama-3.3-70b-versatile`
- `TOP_K=3`

## Database schema

The backend auto-creates the required log table on startup:

```sql
CREATE TABLE IF NOT EXISTS usage_log (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    pdf_name TEXT,
    answer_length INTEGER
);
```

To make uploaded documents durable across serverless invocations, the backend also auto-creates:

```sql
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    pdf_name TEXT NOT NULL,
    chunks JSONB NOT NULL,
    faiss_index BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

The `faiss_index` column name is retained for database compatibility. New records store a small retrieval-version marker; rankings are recomputed from the persisted chunks on each request, so existing document rows remain readable without FAISS.

## Local development

### 1. Start the backend

Use Python 3.11 if possible.

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Vercel deployment

1. Push this repository to GitHub.
2. Import the repository into Vercel.
3. Keep the included `vercel.json` file.
4. Add `DEEPSEEK_API_KEY`, `SMARTDOC_GROQ_API_KEY` (backup), and `POSTGRES_URL` in the Vercel project settings.
5. Create a Vercel Postgres database and copy its connection string into `POSTGRES_URL`.
6. Deploy.

The included `vercel.json` routes all `/api/*` traffic to the FastAPI service and everything else to the Vue frontend.

## API endpoints

- `GET /api/health`
- `POST /api/upload`
- `POST /api/ask`
- `GET /api/insights`

## Retrieval behavior

The retrieval process uses the same chunking and top-k flow as before. Instead of loading a large transformer model at cold start, it tokenizes chunks and the question, computes sparse TF-IDF vectors, and ranks chunks by cosine similarity. This is deterministic, fast for typical uploaded documents, and suitable for Vercel's serverless bundle limit.

### Answer provider configuration

For answer generation, configure `DEEPSEEK_API_KEY` as the primary provider and `SMARTDOC_GROQ_API_KEY` as the backup provider. SmartDoc tries DeepSeek first, then Groq if DeepSeek fails. Optional overrides are `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `GROQ_BASE_URL`, and `GROQ_MODEL`.

The API now keeps the application available if Postgres is temporarily unavailable during a serverless cold start. `/api/health` still responds so configuration problems are visible, while database-backed upload, chat, and insights requests return their normal error details until the database is reachable.

If both hosted answer providers are unavailable, SmartDoc returns a deterministic extractive answer from the retrieved document passages instead of failing the request. This CPU-safe fallback avoids downloading a large open-source model into the Vercel function bundle.
