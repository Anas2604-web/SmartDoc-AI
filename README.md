# SmartDoc AI

SmartDoc AI is a full-stack document Q&A app built with Vue 3, Vite, Tailwind CSS, and FastAPI. It uses Retrieval-Augmented Generation (RAG) to answer questions from uploaded PDFs, stores document indexes in Postgres-backed persistence for Vercel serverless compatibility, and logs query analytics in Vercel Postgres.

## Stack

- Frontend: Vue 3 + Vite + Tailwind CSS
- Backend: FastAPI
- LLM: DeepSeek API through the OpenAI Python SDK
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Vector search: FAISS
- Database: Vercel Postgres

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
- Generate local embeddings with `all-MiniLM-L6-v2`
- Store document chunks and serialized FAISS indexes in Postgres
- Retrieve top 3 chunks for each question
- Ask DeepSeek to answer strictly from retrieved context
- Return grounded answers with source chunks
- Log question text, timestamp, PDF name, and answer length
- Show insights for:
  - most asked questions
  - total questions asked
  - questions per day

## Environment variables

Set these in Vercel for the `api` service:

- `DEEPSEEK_API_KEY`
- `POSTGRES_URL`

Optional:

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-chat`
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

## Local development

### 1. Start the backend

Use Python 3.11 if possible.

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --break-system-packages
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
4. Add `DEEPSEEK_API_KEY` and `POSTGRES_URL` in the Vercel project settings.
5. Create a Vercel Postgres database and copy its connection string into `POSTGRES_URL`.
6. Deploy.

The included `vercel.json` routes all `/api/*` traffic to the FastAPI service and everything else to the Vue frontend.

## API endpoints

- `GET /api/health`
- `POST /api/upload`
- `POST /api/ask`
- `GET /api/insights`

## Notes

- The first embedding request may be slower because the sentence-transformers model needs to initialize.
- The app stores the serialized FAISS index in Postgres so uploaded PDFs remain queryable across serverless invocations.
- DeepSeek answers are constrained with the prompt: `Answer only using the provided context. If the answer is not in the context, say so.`
