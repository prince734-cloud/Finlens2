# FinLens — AI Financial Intelligence & Investment Research Platform

FinLens is a finance-focused AI application that combines semantic document search, company fundamentals, mutual fund analysis, and investment recommendation logic in one platform. It is designed for researchers, students, and investors who want explainable, grounded answers instead of opaque generic financial chat.

The platform uses a Retrieval-Augmented Generation (RAG) pipeline over uploaded PDF financial documents and curated market datasets, then routes user questions to the appropriate analysis path: document Q&A, company financial research, mutual fund analysis, recommendation scoring, or general financial education.

## Why FinLens

- Upload annual reports and financial PDFs and query them naturally
- Search across company filings, fund factsheets, and structured datasets
- Compare companies using audited metrics and ratio analysis
- Evaluate portfolio-fit recommendations using user risk profile and goals
- Keep answers grounded with source citations and clear disclaimers
- Run locally with SQLite + Chroma by default, or move to PostgreSQL/Railway/Render in production

## Core Features

### 1. Document Intelligence
- Upload PDF documents such as annual reports, investor presentations, and fund documents
- Parse and split documents into semantic chunks
- Store chunk embeddings in ChromaDB
- Retrieve relevant passages with hybrid search and reranking
- Return citations with every answer

### 2. Financial Research
- Query tracked companies by ticker or name
- Review historical financial metrics including revenue, profit, leverage, ROE/ROCE, and market cap
- Compare business sectors and industries using structured research endpoints
- Access mutual fund metadata, AUM, expense ratios, risk category, and historical return data

### 3. Investment Recommendation Engine
- Capture investor preferences including amount, monthly contribution, risk tolerance, horizon, and objective
- Apply deterministic filtering rules and score candidates
- Rank assets according to suitability without hidden black-box logic
- Explain why a recommendation fits the user profile

### 4. AI Analyst Workflow
- Route incoming queries to the correct specialist pipeline
- Handle document Q&A, company analysis, mutual-fund evaluation, and financial concept explanations
- Keep LLM output constrained to verified context and regulatory disclaimer language

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy + async SQLite/PostgreSQL
- ChromaDB for vector retrieval
- LangChain + API-based LLM providers
- PyMuPDF for PDF ingestion
- Pydantic for validation and settings

### Frontend
- React + Vite
- Tailwind CSS
- Axios for API requests
- Lucide icons for UI components

### AI / Retrieval Stack
- Hybrid retrieval pipeline for financial document search
- Optional cross-encoder reranking when enabled
- LLM providers: Groq, Mistral, Anthropic, Gemini
- Embedding providers: Hugging Face Inference API, Gemini, Mistral, or lightweight fallbacks

## Project Structure

```text
FinLens/
├── .env.example
├── .env
├── Dockerfile
├── requirements.txt
├── railway.toml
├── render.yaml
├── pyrightconfig.json
├── README.md
├── backend/
│   ├── __init__.py
│   └── app/
│       ├── api/
│       │   ├── chat.py
│       │   ├── documents.py
│       │   ├── kpis.py
│       │   ├── profile.py
│       │   ├── recommendations.py
│       │   └── research.py
│       ├── config.py
│       ├── data/
│       │   ├── company_data.py
│       │   ├── mutual_fund_data.py
│       │   └── chroma_db/
│       ├── database/
│       │   ├── connection.py
│       │   └── models.py
│       ├── extraction/
│       │   └── kpi_extractor.py
│       ├── main.py
│       ├── rag/
│       │   ├── analyst_service.py
│       │   ├── chain.py
│       │   ├── chunking.py
│       │   ├── citations.py
│       │   ├── embeddings.py
│       │   ├── hybrid_search.py
│       │   ├── intent_router.py
│       │   ├── loader.py
│       │   ├── query_rewriter.py
│       │   ├── reranker.py
│       │   └── retriever.py
│       ├── recommendation/
│       │   ├── candidate_generator.py
│       │   ├── filters.py
│       │   ├── ranking.py
│       │   └── scoring.py
│       ├── services/
│       │   ├── document_service.py
│       │   └── llm_service.py
│       └── utils/
│           └── logger.py
├── data/
│   ├── annual_reports/
│   ├── chroma_db/
│   ├── mutual_funds/
│   ├── sample_documents/
│   └── uploads/
├── frontend/
│   ├── README.md
│   ├── package.json
│   ├── vite.config.js
│   ├── public/
│   └── src/
└── tests/
```

## Prerequisites

- Python 3.11 or newer
- Node.js 18+ and npm
- Access to an LLM provider API key (Groq, Mistral, Anthropic, or Gemini)
- Optional: PostgreSQL if you want a production-grade database instead of SQLite

## Quick Start

### 1. Clone and enter the project

```bash
git clone https://github.com/prince734-cloud/Finlens2.git
cd Finlens2
cd FinLens
```

### 2. Create a Python environment

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# or
source .venv/bin/activate # macOS / Linux
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the sample environment file and update it with your keys:

```bash
copy .env.example .env
```

Then edit `.env` with your provider settings. At minimum, set a valid LLM API key and select a provider. Example:

```env
DATABASE_URL="sqlite+aiosqlite:///./finlens.db"
VECTOR_STORE_BACKEND="chroma"
LLM_PROVIDER="groq"
GROQ_API_KEY="your_groq_key_here"
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

The project also supports provider-specific values such as:

- `MISTRAL_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `HF_TOKEN` for Hugging Face inference

### 5. Start the backend

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 6. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

- http://localhost:5173

## Environment Configuration

The app reads settings from the root `.env` file via `backend/app/config.py`.

Key settings include:

- `APP_NAME`, `ENVIRONMENT`, `DEBUG`, `HOST`, `PORT`
- `DATABASE_URL` for SQLite or PostgreSQL
- `VECTOR_STORE_BACKEND` for ChromaDB or pgvector-style integrations
- `LLM_PROVIDER` and provider-specific model names
- `EMBEDDING_PROVIDER` for vector generation strategy
- `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K_RETRIEVAL`, `TOP_K_RERANKED`

A full sample configuration is included in `.env.example`.

## How the Platform Works

### Document Q&A Flow
1. A PDF is uploaded via `/api/v1/documents/upload`
2. The document is saved locally and registered in the database
3. The file is parsed and chunked into manageable text segments
4. Chunks are embedded and indexed in Chroma
5. The user asks a question through the chat endpoint
6. The system retrieves the most relevant passages, reranks them, and creates a grounded answer with citations

### Research Flow
1. The system detects whether the user is asking about a company, mutual fund, portfolio fit, or concept
2. It fetches relevant structured data from SQL tables
3. It synthesizes a response using the available audited metrics
4. It returns well-structured answer blocks and risk-aware disclaimers

### Recommendation Flow
1. The app loads or creates a demo investor profile
2. It calculates candidate assets from company and fund datasets
3. It applies hard filters based on risk, horizon, and objective
4. It scores and ranks investments using deterministic logic
5. It returns explainable suitability results

## API Overview

### Health and Status
- `GET /api/v1/health`
- `GET /api/v1/status`

### Documents
- `GET /api/v1/documents`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/{document_id}/chunks`
- `DELETE /api/v1/documents/{document_id}`

### Chat
- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`
- `GET /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}`
- `DELETE /api/v1/chat/sessions/{session_id}`

### Research
- `GET /api/v1/research/companies`
- `GET /api/v1/research/companies/{symbol_or_id}`
- `POST /api/v1/research/companies`
- `GET /api/v1/research/mutual-funds`
- `GET /api/v1/research/mutual-funds/{fund_id}`

### Profile and Recommendations
- `GET /api/v1/profile`
- `POST /api/v1/profile`
- `PUT /api/v1/profile`
- `GET /api/v1/recommendations`
- `POST /api/v1/recommendations/evaluate`

## Deployment Options

### Local Development
This is the simplest path for evaluation and testing. SQLite + local ChromaDB is enabled by default and works well for demos and local research.

### Vercel + Frontend
The frontend is configured as a Vite app. You can deploy it to Vercel using the frontend directory as the root project.

Set:

```text
VITE_API_BASE_URL=https://<your-backend-domain>/api/v1
```

### Railway / Render / Docker
The project includes `Dockerfile`, `railway.toml`, and `render.yaml` for cloud deployments.

Recommended production pattern:

- Backend deployed on Railway or Render
- PostgreSQL database for relational data
- Chroma persistence or a managed vector backend
- Environment variables set through platform config

## Testing

The backend includes a set of pytest-based validation tests, including:

- health checks
- KPI extraction
- RAG pipeline validation
- company and research queries
- recommendation scoring

Run tests with:

```bash
pytest
```

If you want to run a smaller subset:

```bash
pytest backend/tests/test_health.py
```

## Troubleshooting

### Missing LLM key
If the app starts but AI answers fail, confirm that the selected provider has a valid API key in `.env` and that the provider matches the configured `LLM_PROVIDER`.

### Chroma / vector issues
Delete or rebuild `data/chroma_db` if the vector store becomes corrupted or inconsistent.

### Database connection errors
Verify `DATABASE_URL` points to an existing database. For local work, SQLite usually works without extra setup.

### Frontend cannot reach backend
Ensure the frontend dev server can connect to the backend on `http://127.0.0.1:8000` and that `CORS_ORIGINS` includes your frontend origin.

## Regulatory Disclaimer

FinLens is designed for educational and research use. It does not provide personalized financial advice, legal advice, or guarantees of investment returns. Every AI-generated answer includes a disclaimer and should be treated as decision-support information, not a substitute for a licensed financial advisor or a professional investment recommendation.

## License

This project is provided as-is for research, learning, and prototype development. If you intend to deploy it in production or commercial environments, confirm the licensing requirements for any third-party models, packages, and data sources you use.

## Contributing

Contributions are welcome. For major changes, please open an issue first so the architecture and scope can be reviewed before implementation.

## Contact

For project questions, deployment assistance, or collaboration inquiries, reach out through the repository maintainer or the project issue tracker.

