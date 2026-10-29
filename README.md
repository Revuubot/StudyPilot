# StudyPilot 🚀

Production-grade AI study co-pilot that converts YouTube lectures and PDFs into structured notes, provides RAG-based question answering with citations, and tracks your productivity.

## ✨ Core Features
- **YouTube/PDF to Notes**: Get Topic, Key Concepts, Detailed Notes, and TL;DR instantly.
- **RAG Question Answering**: Ask questions about your notes and get answers with citations and source snippets.
- **Semantic Search**: Search across your entire knowledge base using meaning, not just keywords.
- **Real-time Streaming**: Watch as answers are generated via WebSockets.
- **Productivity Dashboard**: Track time saved and engagement metrics.
- **Whisper Fallback**: Automatically transcribes videos without captions using OpenAI Whisper.

## 🛠 Tech Stack
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL + pgvector, Celery, Redis.
- **Frontend**: React 18, Tailwind CSS, Recharts, Vite.
- **AI**: Gemini 1.5 Flash (LLM & Embeddings), OpenAI Whisper.

## 🚀 Getting Started

### Prerequisites
- **Docker Desktop** (Recommended)
- OR **Python 3.11+**, **Node.js 18+**, and a **PostgreSQL (pgvector)** instance.

### Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Add your API Keys:
   - `GEMINI_API_KEY`: Get from [Google AI Studio](https://aistudio.google.com/)
   - `OPENAI_API_KEY`: (Optional) For Whisper fallback.

### Option 1: Docker (Recommended)
Launch the full stack in one command:
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

### Option 2: Manual Setup (No Docker)
1. **Database**: Ensure you have PostgreSQL with the `vector` extension installed.
2. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. **Celery**:
   ```bash
   cd backend
   celery -A tasks:celery_app worker --loglevel=info
   ```

## 🧪 Testing
- **Backend**: `pytest` (from the backend directory)
- **Frontend**: `npm test` (from the frontend directory)

## 📡 API Endpoints
- `POST /api/auth/register` / `login`: JWT Authentication.
- `POST /api/summarise/youtube`: URL to notes.
- `POST /api/summarise/pdf`: File to notes.
- `POST /api/ask`: RAG question answering.
- `GET /api/search?q=...`: Semantic search.
- `GET /api/analytics/dashboard`: Productivity metrics.
- `WS /ws/ask`: Streaming RAG answers.

## 📄 License
MIT
