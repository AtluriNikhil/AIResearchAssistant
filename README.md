# AI Research Assistant

## Project Report

AI Research Assistant is a full-stack document question-answering system built with FastAPI, Next.js, FAISS, SQLite, LangGraph, and configurable LLM providers. The project lets a user upload research material, resumes, reports, articles, or other text-heavy documents, then ask natural-language questions against those documents through a guided multi-agent workflow.

The application is designed as a practical Retrieval-Augmented Generation (RAG) system. Instead of sending the entire document to an LLM every time, the backend extracts text, splits it into chunks, embeds those chunks, stores them in FAISS, retrieves the most relevant chunks for each question, and then asks an LLM to answer strictly from the retrieved context.

This README is written as a project report. It explains what the project does, why the architecture is useful, why this architecture was chosen, how the system flows internally, which technologies are used, and how to run and maintain it.

---

## 1. Executive Summary

The project solves a common research problem: users often have long documents but need fast, accurate, context-aware answers. Reading a whole PDF or report manually is slow, and asking a generic chatbot without grounding can cause hallucinated answers. This system improves that workflow by combining:

- Document ingestion
- Text extraction
- Chunking
- Embedding-based retrieval
- Multi-document selection
- Multi-agent answer generation
- Conversation memory
- A browser-based chat interface

The project is good because it is not just a simple chatbot. It has a layered architecture that separates the user interface, backend API, retrieval logic, agent workflow, storage, logging, and model-provider configuration. This makes the project easier to understand, debug, extend, and explain in interviews or demos.

---

## 2. What This Project Does

The application supports the following core use cases:

- Upload PDF, DOCX, HTML, HTM, or TXT documents.
- Extract meaningful text from uploaded files.
- Split extracted text into overlapping chunks.
- Convert chunks into vectors using a configurable embedding provider.
- Store document vectors in FAISS.
- Keep each uploaded document in its own FAISS index for clean multi-document retrieval.
- Let the user select one document, all documents, or a custom set of documents.
- Ask questions through a chat interface.
- Retrieve only the most relevant chunks for the question.
- Use a multi-agent workflow to research, summarize, critique, and edit the final response.
- Store conversation history in SQLite so follow-up questions can use previous context.
- Show workflow progress in the frontend.
- Log API, agent, database, and parser activity for debugging.

---

## 3. Why This Project Is Useful

This project is useful because it demonstrates how a real-world AI assistant should be structured. A naive chatbot sends a prompt directly to an LLM and hopes the answer is correct. This project adds retrieval, grounding, validation, and memory around the LLM.

Key strengths:

- Grounded answers: The assistant is instructed to answer only from retrieved document context.
- Better scalability: Documents are indexed once, then searched efficiently.
- Multi-document support: Users can upload and query multiple documents separately.
- Provider flexibility: The chat model can use Anthropic or OpenAI, while embeddings can use local hashing, Voyage, or OpenAI.
- Modular architecture: Each layer has a focused responsibility.
- Debuggability: Rotating logs make it easier to inspect failures.
- Strong demo value: It includes frontend UI, backend APIs, storage, memory, and AI orchestration.

---

## 4. Why This Architecture Was Chosen

The architecture was chosen because document Q&A has multiple responsibilities that should not be mixed into one large function.

The main design decisions are:

### 4.1 Separate Frontend and Backend

The frontend is responsible for the user experience: uploading files, selecting documents, sending questions, showing answers, and displaying workflow progress.

The backend is responsible for the AI and data work: parsing files, generating embeddings, searching vectors, running agents, and persisting memory.

This separation is good because the frontend can evolve independently from the AI pipeline. The backend can also be tested through API calls without needing the browser.

### 4.2 RAG Instead of Full-Document Prompting

The system uses Retrieval-Augmented Generation because sending full documents to an LLM is inefficient and expensive. Large documents may exceed token limits, and unrelated content can reduce answer quality.

RAG solves this by:

1. Splitting documents into smaller chunks.
2. Embedding each chunk.
3. Searching for the chunks most similar to the user query.
4. Sending only those relevant chunks to the LLM.

This gives better focus, lower token usage, and more grounded answers.

### 4.3 FAISS for Vector Search

FAISS was chosen because it is fast, local, and well-suited for vector similarity search. It avoids needing an external vector database during development.

The project uses FAISS in two ways:

- Legacy single-index storage through `backend/db/faiss_store.py`.
- Current multi-document storage through `backend/db/multi_doc_store.py`.

The multi-document design is better for user control because each document gets its own index under `backend/db/documents/`.

### 4.4 LangGraph for Agent Orchestration

The multi-agent flow is represented with LangGraph. LangGraph gives the workflow a clear state object and explicit nodes.

The current graph is:

```text
User Query
    |
    v
Research Agent
    |
    v
Summarizer Agent
    |
    v
Critic Agent
    |
    +--> Editor Agent, if gaps are found
    |
    +--> Skip Editor, if no gaps are found
    |
    v
Final Answer
```

This architecture is good because each agent has one job:

- Research Agent retrieves context.
- Summarizer Agent creates the first answer.
- Critic Agent checks quality and missing information.
- Editor Agent improves the answer if needed.

This mirrors how a human research assistant might work: gather evidence, draft, review, then polish.

### 4.5 SQLite for Conversation Memory

SQLite was chosen because it is simple, local, and reliable for development. It stores sessions and messages without needing an external database server.

Conversation memory is useful because follow-up questions often depend on earlier messages. The backend formats recent conversation history and passes it into the summarizer so the model can understand follow-up context.

### 4.6 Configurable Model Providers

The project originally depended on OpenAI. It now supports Anthropic for LLM calls through `backend/utils/llm_client.py`.

Because Anthropic does not provide embeddings directly, the project separates LLM providers from embedding providers:

- LLM provider: Anthropic or OpenAI
- Embedding provider: local hash, Voyage, or OpenAI

This is a stronger architecture because generation and retrieval are separate concerns.

---

## 5. High-Level Architecture

```text
Browser / Next.js Frontend
    |
    | HTTP requests with Axios
    v
FastAPI Backend
    |
    +--> Upload API
    |       |
    |       +--> Document Parser
    |       +--> Chunker
    |       +--> Embedding Provider
    |       +--> FAISS Multi-Document Store
    |
    +--> Chat API
            |
            +--> SQLite Conversation Memory
            +--> Research Agent
            +--> FAISS Retrieval
            +--> Summarizer Agent
            +--> Critic Agent
            +--> Editor Agent
            +--> LLM Provider
```

---

## 6. Main Data Flow

### 6.1 Document Upload Flow

When a user uploads a document:

1. Frontend sends the file to `POST /upload-v2`.
2. Backend validates the file extension.
3. Backend saves the file temporarily.
4. `document_parser.py` extracts text based on file type.
5. Extracted text is split into overlapping chunks.
6. Each chunk is embedded through `embeddings.py`.
7. A FAISS index is created for that document.
8. Metadata and document info are saved beside the index.
9. The temporary uploaded file is removed.
10. The frontend refreshes the document list.

Stored per-document files:

```text
backend/db/documents/[safe_doc_id]/
    index.bin
    metadata.pkl
    info.pkl
```

### 6.2 Question Answering Flow

When a user asks a question:

1. Frontend sends the query to `POST /ask-v2`.
2. Backend creates or reuses a conversation session.
3. User message is stored in SQLite.
4. Recent conversation history is loaded.
5. Orchestrator starts the LangGraph workflow.
6. Research Agent embeds the query and searches selected FAISS indexes.
7. Summarizer Agent answers using only retrieved chunks.
8. Critic Agent checks the answer for gaps or unsupported content.
9. Editor Agent refines the answer when needed.
10. Final answer is stored in SQLite.
11. Frontend displays the answer and workflow log.

---

## 7. Backend Architecture

The backend is a FastAPI application located in `backend/`.

### Important Backend Files

```text
backend/main.py
```

Defines the FastAPI app, CORS settings, upload endpoints, chat endpoints, session endpoints, stats endpoint, and workflow diagram endpoint.

```text
backend/config.py
```

Loads environment variables from the project root `.env`.

```text
backend/utils/document_parser.py
```

Extracts text from PDF, DOCX, HTML, HTM, and TXT files.

```text
backend/utils/embeddings.py
```

Provides embeddings through a configurable provider:

- `local_hash`
- `voyage`
- `openai`

```text
backend/utils/llm_client.py
```

Provides a common LLM calling interface for:

- Anthropic
- OpenAI

```text
backend/db/multi_doc_store.py
```

Stores one FAISS index per uploaded document.

```text
backend/db/sqlite_memory.py
```

Stores conversation sessions and messages in SQLite.

```text
backend/agents/
```

Contains the multi-agent workflow:

- `research_agent.py`
- `summarizer_agent.py`
- `critic_agent.py`
- `editor_agent.py`
- `langgraph_nodes.py`
- `langgraph_workflow.py`
- `orchestrator.py`
- `agent_state.py`

---

## 8. Frontend Architecture

The frontend is a Next.js application located in `frontend/`.

### Important Frontend Files

```text
frontend/components/ChatBox.tsx
```

Main UI component. It handles:

- Uploading documents
- Fetching document list
- Selecting documents
- Sending chat questions
- Showing answers
- Showing workflow progress
- Tracking current session id

```text
frontend/pages/index.tsx
```

Renders the main chat page.

```text
frontend/styles/globals.css
```

Tailwind-based global styles and reusable component classes.

```text
frontend/package.json
```

Defines frontend dependencies and scripts.

---

## 9. Technology Stack

### Backend

- Python 3.11
- FastAPI for API routes
- Uvicorn for running the backend server
- Pydantic for request and response schemas
- FAISS CPU for vector similarity search
- NumPy for vector operations
- SQLite for conversation memory
- LangGraph for multi-agent workflow orchestration
- python-dotenv for environment loading
- pdfplumber for PDF text extraction
- python-docx for DOCX parsing
- BeautifulSoup4 and lxml for HTML parsing
- Anthropic SDK for Claude calls
- OpenAI SDK as an optional provider
- Voyage AI SDK as an optional embedding provider

### Frontend

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- Axios for API requests
- Radix UI icons
- TanStack React Query dependency included for future data-fetching expansion

### Storage

- FAISS indexes saved locally under `backend/db/`
- SQLite database saved as `backend/db/conversations.db`
- Logs saved under `backend/logs/`

---

## 10. Environment Variables

Create a `.env` file in the project root.

Recommended Anthropic setup:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS=2048

EMBEDDING_PROVIDER=local_hash
LOCAL_EMBEDDING_DIM=384

VECTOR_DB_PATH=./backend/db/documents
BACKEND_PORT=8000
```

Optional Voyage embeddings:

```env
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=your_voyage_api_key
EMBEDDING_MODEL=voyage-3.5
```

Optional OpenAI configuration:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o-mini

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

Important note:

If you change `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, or `LOCAL_EMBEDDING_DIM`, re-upload documents. Existing FAISS indexes must have the same vector dimension as new query embeddings.

---

## 11. Installation

### 11.1 Prerequisites

Install:

- Python 3.8 or newer
- Node.js 18 or newer
- An Anthropic API key

### 11.2 Backend Setup on Windows

From the project root:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant
python -m venv venv
venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 11.3 Frontend Setup on Windows

If `npm` is not recognized, Node may be installed but not on PATH. This project has been run successfully using the full Node path:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\frontend
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' install
```

If `npm` works normally on your machine:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\frontend
npm install
```

---

## 12. Commands to Run the Project

Run the backend in one terminal:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\backend
..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Run the frontend in another terminal:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\frontend
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' run dev
```

Open the application:

```text
http://localhost:3000
```

Check backend health:

```text
http://localhost:8000/health
```

Expected health response:

```json
{"status":"ok"}
```

---

## 13. API Endpoints

### Health

```text
GET /health
```

Returns backend health status.

### Documents

```text
GET /documents
```

Returns uploaded documents from both legacy and multi-document stores.

```text
POST /upload
```

Legacy upload endpoint that stores all documents in one FAISS index.

```text
POST /upload-v2
```

Current upload endpoint. Stores each document in its own FAISS index.

### Query

```text
POST /ask
```

Legacy single-index RAG query.

```text
POST /ask-agents
```

Legacy multi-agent query using the single FAISS index.

```text
POST /ask-v2
```

Current multi-document agent query endpoint used by the frontend.

Example request:

```json
{
  "query": "Summarize the document",
  "top_k": 5,
  "doc_ids": ["example_pdf"],
  "session_id": null
}
```

### Sessions

```text
POST /sessions/create
GET /sessions/{session_id}/history
DELETE /sessions/{session_id}
GET /sessions
```

### Utilities

```text
GET /workflow/diagram
GET /stats
```

---

## 14. Multi-Agent Workflow Details

### Research Agent

The Research Agent converts the user query into an embedding, searches FAISS, and returns the top matching chunks from selected documents.

Why it is important:

- It keeps the LLM grounded.
- It reduces prompt size.
- It lets the app answer from specific documents.

### Summarizer Agent

The Summarizer Agent receives the retrieved chunks and creates the first answer. Its prompt explicitly tells the LLM to answer only from the provided context.

Why it is important:

- It turns raw chunks into a readable answer.
- It handles simple and complex questions differently.
- It includes conversation context for follow-up questions.

### Critic Agent

The Critic Agent evaluates whether the answer is accurate and whether it adds unsupported details.

Why it is important:

- It helps reduce hallucination.
- It checks whether relevant information was missed.
- It decides whether editing is needed.

### Editor Agent

The Editor Agent refines the answer using the critique and the original context.

Why it is important:

- It improves clarity.
- It removes unsupported content.
- It adds missing context when available.

---

## 15. Why the Architecture Is Good

This architecture is good because it applies software engineering separation of concerns to an AI system.

### Maintainability

Each part has a clear role. If retrieval has an issue, inspect the Research Agent or FAISS store. If model calls fail, inspect `llm_client.py`. If parsing fails, inspect `document_parser.py`.

### Extensibility

New document types can be added in `document_parser.py`. New LLM providers can be added in `llm_client.py`. New embedding providers can be added in `embeddings.py`. New agents can be added to the LangGraph workflow.

### Debuggability

Logs are separated by responsibility:

- `backend/logs/api.log`
- `backend/logs/agents.log`
- `backend/logs/database.log`
- `backend/logs/parser.log`

### Cost Control

RAG retrieves only relevant chunks instead of sending full documents to the LLM.

### Better Answer Quality

The multi-agent pipeline gives the model several roles: retrieval, answer generation, critique, and editing. This is more robust than a single prompt.

### Local Development Friendly

FAISS and SQLite run locally, so the project does not need external infrastructure beyond the selected LLM API.

---

## 16. Current Limitations

The project is strong for local RAG demos and research-assistant workflows, but there are limitations:

- `local_hash` embeddings are a no-key fallback and are less semantic than Voyage or OpenAI embeddings.
- Uploaded documents are stored locally, not in cloud storage.
- There is no user authentication.
- The frontend API base URL is hardcoded to `http://localhost:8000`.
- The legacy `/upload` and `/ask` routes still exist alongside the newer multi-document flow.
- There is no automated test suite yet.
- Some frontend text contains encoding artifacts inherited from earlier content.

---

## 17. Clearing Documents and Memory

Stop the backend first, then run:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant
Remove-Item -Recurse -Force backend\db\documents
Remove-Item -Force backend\db\conversations.db
Remove-Item -Force backend\db\conversations.db-journal -ErrorAction SilentlyContinue
Remove-Item -Force backend\db\*.bin, backend\db\*.pkl -ErrorAction SilentlyContinue
```

Then restart the backend. The database and document folders will be recreated automatically.

---

## 18. Troubleshooting

### Backend starts and then stops

Run the backend from a real PowerShell terminal, not the VS Code run button:

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\backend
..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Avoid `--reload` if the Windows reloader exits unexpectedly.

### Backend says `Provider: openai`

Check `.env`:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
```

Restart the backend after editing `.env`.

### `npm` is not recognized

Use the full Node path:

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' --version
```

### PowerShell blocks `npm.ps1`

Use `npm.cmd`:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run dev
```

### Chat returns empty answer

The frontend now displays a fallback message if the backend returns an empty answer. Check:

```text
backend/logs/agents.log
backend/logs/api.log
```

The most common causes are invalid model name, missing API key, old backend process, or stale `.env` values.

### FAISS dimension mismatch

Clear and re-upload documents if you change embedding provider or embedding dimension.

---

## 19. Development Notes

### Backend compile check

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\backend
..\venv\Scripts\python.exe -m compileall .
```

### Frontend TypeScript check

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\frontend
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npx.cmd' tsc --noEmit
```

### Production build

```powershell
cd C:\Users\ADMIN\AI-Research-Assistant\frontend
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' run build
```

---

## 20. Security Notes

- Never commit `.env`.
- Rotate API keys if they are accidentally pasted into chat, logs, screenshots, or Git.
- Uploaded documents and SQLite memory are stored locally under `backend/db/`.
- CORS is currently open for development with `allow_origins=["*"]`; restrict it before production deployment.

---

## 21. Future Improvements

Good next steps:

- Add authentication and per-user document isolation.
- Replace hardcoded frontend API URL with an environment variable.
- Add automated backend tests for upload, retrieval, and session memory.
- Add frontend tests for upload and chat behavior.
- Add delete-document API endpoint.
- Add document preview and source citations in answers.
- Add streaming LLM responses.
- Add Docker setup for easier deployment.
- Add production-ready CORS configuration.
- Add evaluation tests for answer faithfulness.
- Use Voyage or another semantic embedding provider for stronger retrieval quality.

---

## 22. Final Summary

AI Research Assistant is a strong full-stack AI project because it combines practical product behavior with a clear AI architecture. It is more than a chatbot: it is a document ingestion, retrieval, memory, and multi-agent reasoning system.

The architecture is good because it is modular, explainable, and extensible. The frontend focuses on user interaction, FastAPI exposes clean endpoints, FAISS handles retrieval, SQLite stores memory, LangGraph coordinates agents, and provider wrappers keep the LLM and embedding layers flexible.

This makes the project suitable for demos, learning, interviews, portfolio presentation, and future extension into a production-grade research assistant.
