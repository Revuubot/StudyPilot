# 🚀 StudyPilot — AI-Powered Study Co-Pilot

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL_pgvector-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**Transform lengthy YouTube lectures and dense PDF textbooks into structured notes, interactive study partners, and searchable knowledge bases.**

[Explore Features](#-core-capabilities) • [Key Use Cases](#-real-world-use-cases) • [Architecture](#-system-architecture) • [Quickstart](#-getting-started) • [API Reference](#-api-endpoints)

</div>

---

## 📖 Overview

**StudyPilot** is an end-to-end, production-ready AI study platform engineered for students, researchers, and lifelong learners. Instead of spending hours scrubbing through video timelines or highlighting hundreds of PDF pages, StudyPilot automates note synthesis, provides source-grounded question answering (RAG) with exact citations, and tracks your personal study productivity over time.

---

## ✨ Core Capabilities

### 1. 🎥 Multi-Source Content Ingestion
- **YouTube Lectures**: Ingests public YouTube videos, extracts native closed captions, or falls back seamlessly to **OpenAI Whisper** audio transcription when captions are missing or auto-generated captions are low quality.
- **Academic PDFs**: Extracts structured text and chapter content from textbooks, syllabi, research papers, and slide decks.

### 2. 📝 Structured Note Synthesis
- Powered by **Google Gemini 1.5 Flash**, converting raw lectures into clean, scannable study guides:
  - **Topic & Overview**: High-level framing of the subject matter.
  - **Key Concepts**: Essential terms, definitions, and theories.
  - **Detailed Explanations**: Deep dives into step-by-step methodologies and proofs.
  - **TL;DR**: Executive summary for quick pre-exam refresher.

### 3. 🧠 Grounded Q&A with Citations (RAG)
- Uses **PostgreSQL + pgvector** with 768-dimensional `text-embedding-004` vector embeddings.
- Every question retrieves the most relevant semantic chunks and generates answers backed by **verifiable source citations** (video timestamp or PDF page/source chunk) to prevent AI hallucinations.

### 4. ⚡ Real-Time Streaming & WebSocket Support
- Watch responses stream token-by-token over `/ws/ask` for zero-latency feedback during intensive study sessions.

### 5. 🔍 Semantic Knowledge Search
- Find concepts across your entire library using conceptual meaning rather than exact keyword matches (e.g. searching *"how gradient descent updates weights"* will surface relevant calculus and machine learning notes even if the exact phrase isn't present).

### 6. 📊 Productivity & Study Analytics
- Visual dashboard built with **Recharts** displaying:
  - Estimated hours saved (reading/listening time vs. synthesis time).
  - Study streaks and weekly question trends.
  - Top revisited notes and knowledge retention metrics.

### 7. 🛡️ Enterprise-Grade Foundation
- **Authentication**: JWT-based authentication with bcrypt password hashing.
- **Middleware**: Sliding-window rate limiting per IP and structured request logging.
- **Background Tasks**: Celery worker integration backed by Redis for offloading long-running transcription and embedding generation.

---

## 🎯 Real-World Use Cases

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                              USE CASES                                 │
 ├────────────────────────────────────────────────────────────────────────┤
 │  🎓 University Students:                                               │
 │     Synthesize 2-hour university lectures & 80-page slide decks into   │
 │     exam-ready cheat sheets and quiz yourself with interactive Q&A.    │
 │                                                                        │
 │  🔬 Researchers & Academics:                                           │
 │     Ingest whitepapers, cross-query methodologies, and verify facts    │
 │     with exact page and passage citations.                             │
 │                                                                        │
 │  💻 Developers & Tech Enthusiasts:                                     │
 │     Convert conference talks, tech keynotes, and coding tutorials into │
 │     scannable reference documentation.                                 │
 │                                                                        │
 │  📚 Self-Paced Learners & Bootcamps:                                   │
 │     Maintain a centralized, searchable semantic knowledge base across │
 │     multiple courses and monitor weekly study streaks.                 │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗 System Architecture

```
                  ┌────────────────────────────────────────┐
                  │          React 18 Frontend             │
                  │   (Vite + Tailwind CSS + Recharts)     │
                  └───────────────────┬────────────────────┘
                                      │ HTTP / WebSocket
                                      ▼
                  ┌────────────────────────────────────────┐
                  │         FastAPI Backend API            │
                  │  (JWT Auth, Rate Limiter, Middleware)  │
                  └──────┬──────────────────────────┬──────┘
                         │                          │
        Async Background │ Jobs      Direct Queries │
                         ▼                          ▼
              ┌─────────────────────┐   ┌────────────────────────┐
              │   Celery + Redis    │   │  PostgreSQL + pgvector │
              │ (Whisper & Batches) │   │ (Notes, Users, Vectors)│
              └──────────┬──────────┘   └───────────┬────────────┘
                         │                          │
                         └───────────┬──────────────┘
                                     ▼
                        ┌────────────────────────┐
                        │   Google Gemini API    │
                        │ • 1.5 Flash (LLM)      │
                        │ • text-embedding-004   │
                        └────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons, Recharts |
| **Backend API** | FastAPI, Pydantic v2, Python 3.11+, SQLAlchemy 2.0 (Async) |
| **Vector & Relational DB**| PostgreSQL 16 with `pgvector` extension |
| **Background Processing**| Celery, Redis |
| **AI & ML Models** | Google Gemini 1.5 Flash, Gemini `text-embedding-004`, OpenAI Whisper |
| **Containerization** | Docker, Docker Compose |
| **Testing** | Pytest, Vitest, Testing Library |

---

## 🚀 Getting Started

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recommended for seamless one-command setup)
- OR local runtimes: **Python 3.11+**, **Node.js 18+**, and **PostgreSQL with pgvector**
- A **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

---

### Option 1: One-Click Docker Setup (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Revuubot/StudyPilot.git
   cd StudyPilot
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and add your `GEMINI_API_KEY`:
   ```env
   GEMINI_API_KEY="your-gemini-api-key-here"
   ```

3. **Start the application**:
   ```bash
   docker compose up --build
   ```

4. **Access the services**:
   - 🌐 **Web Application**: [`http://localhost:3000`](http://localhost:3000)
   - 📚 **Interactive Swagger API Docs**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
   - 📖 **ReDoc Alternative Docs**: [`http://localhost:8000/redoc`](http://localhost:8000/redoc)

---

### Option 2: Local Manual Setup

#### 1. Database & Cache Services
Ensure PostgreSQL with `pgvector` and Redis are running locally.
```bash
# Example using Docker for databases only
docker run -d --name studypilot-pg -p 5432:5432 -e POSTGRES_USER=studypilot -e POSTGRES_PASSWORD=studypilot -e POSTGRES_DB=studypilot pgvector/pgvector:pg16
docker run -d --name studypilot-redis -p 6379:6379 redis:7-alpine
```

#### 2. Backend API Setup
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Celery Worker (In a separate terminal)
```bash
cd backend
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

celery -A tasks.celery_app worker --loglevel=info
```

#### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [`http://localhost:3000`](http://localhost:3000) in your browser.

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(Required)* | Google AI Studio API key for summarisation & embeddings |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI key for Whisper audio transcription fallback |
| `DATABASE_URL` | `postgresql+asyncpg://studypilot:studypilot@localhost:5432/studypilot` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | `postgresql://studypilot:studypilot@localhost:5432/studypilot` | Sync database connection string for Celery |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis instance for Celery broker & result backend |
| `SECRET_KEY` | `your-secret-key-here` | Secret key for signing JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | JWT access token lifespan in minutes |
| `RATE_LIMIT_PER_MINUTE` | `10` | Maximum requests per minute per IP for sensitive routes |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |

---

## 📡 API Endpoints

### 🔐 Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Create a new user account and obtain access token |
| `POST` | `/api/auth/login` | Authenticate existing credentials and obtain JWT |
| `GET` | `/api/auth/me` | Fetch authenticated user profile |

### 📝 Summarisation & Extraction
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/summarise/youtube` | Extract YouTube transcript and generate structured notes |
| `POST` | `/api/summarise/pdf` | Upload PDF textbook/paper and generate structured notes |

### 🧠 Grounded Q&A & Search
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/ask` | Ask questions over notes with verified citations (RAG) |
| `WS` | `/ws/ask` | WebSocket endpoint for streaming token-by-token Q&A |
| `GET` | `/api/search?q={query}` | Semantic search across the entire personal knowledge base |

### 📊 Analytics & Tasks
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/analytics/dashboard` | Aggregated user metrics, time saved, and trend charts |
| `GET` | `/api/tasks/{task_id}` | Poll background Celery task status (transcription/batch) |
| `GET` | `/health` | Container & orchestrator health check |

---

## 🧪 Testing

### Backend Test Suite (Pytest)
```bash
cd backend
pytest
```
Covers API endpoints, authentication flows, RAG citation accuracy, and asynchronous task execution.

### Frontend Test Suite (Vitest)
```bash
cd frontend
npm test
```
Tests component rendering, authentication state switching, and navigation.

---

## 📂 Project Directory Structure

```text
StudyPilot/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── docker-compose.yml        # Multi-container service definitions
├── README.md                 # Project documentation
├── backend/
│   ├── Dockerfile            # Python/FastAPI container definition
│   ├── requirements.txt      # Python dependencies
│   ├── tasks.py              # Celery background tasks
│   ├── app/
│   │   ├── auth.py           # Password hashing & JWT token verification
│   │   ├── config.py         # Pydantic environment configuration
│   │   ├── database.py       # Async SQLAlchemy session management
│   │   ├── main.py           # FastAPI entrypoint, middleware, routers
│   │   ├── middleware.py     # Request logging & rate limiting
│   │   ├── models.py         # SQLAlchemy ORM models (with pgvector)
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── services.py       # Ingestion, chunking, Gemini & RAG logic
│   │   └── routes/           # REST & WebSocket API route handlers
│   └── tests/                # Pytest unit & integration test suite
└── frontend/
    ├── Dockerfile            # React/Vite container definition
    ├── package.json          # Node dependencies & test scripts
    ├── vite.config.js        # Vite build & Vitest test config
    ├── tailwind.config.js    # Tailwind styling config
    └── src/
        ├── api.js            # Axios client with JWT interceptors
        ├── App.jsx           # Main navigation & state container
        └── components/       # UI Tabs (Summarise, Ask, Search, Analytics)
```

---

## 🤝 Contributing

Contributions, feedback, and feature suggestions are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
