Phase 1 — Document Upload & Ingestion:

User drags a file → Frontend (Next.js)
                         ↓
              FileUpload.tsx captures file
                         ↓
              useDocuments.ts calls uploadDocument()
                         ↓
              lib/api.ts sends POST /api/upload
                         ↓
              Next.js proxy (app/api/upload/route.ts)
                         ↓
              FastAPI backend receives file
                         ↓
              routers/upload.py handles the request
                    ↓              ↓
          Saves file to        Creates Document
          ./storage/           record in PostgreSQL
          folder               (status = "processing")
                    ↓
          services/parser.py
          detects file type and extracts text
               PDF → PyPDF2
               Word → python-docx
               Excel → openpyxl
               Image → pytesseract OCR
                    ↓
          services/chunker.py
          splits text into 512-char chunks
          with 50-char overlap
          (using LangChain RecursiveCharacterTextSplitter)
                    ↓
          services/embedder.py
          converts each chunk to a 384-dim vector
          using all-MiniLM-L6-v2 (runs locally, no API cost)
                    ↓
          services/vector_store.py
          stores vectors + chunk text + metadata
          into ChromaDB (./chroma_db/ folder)
          one collection per user session
                    ↓
          PostgreSQL updated
          (status = "ready", chunk_count = N)
                    ↓
          Frontend shows document as "ready"
          with chunk count in sidebar


Phase 2 — User Asks a Question:

User types question → ChatWindow.tsx
                            ↓
                 handleSend() triggered
                            ↓
                 useChat.ts calls POST /api/chat
                            ↓
                 Next.js proxy (app/api/chat/route.ts)
                            ↓
                 FastAPI routers/chat.py receives question
                            ↓
                 ┌──────────────────────────────┐
                 │     STEP 1 — EMBED QUERY     │
                 │  services/embedder.py         │
                 │  same all-MiniLM-L6-v2 model │
                 │  question → 384-dim vector   │
                 └──────────────┬───────────────┘
                                ↓
                 ┌──────────────────────────────┐
                 │   STEP 2 — RETRIEVE TOP-10   │
                 │  services/vector_store.py    │
                 │  ChromaDB cosine similarity  │
                 │  returns 10 candidate chunks │
                 └──────────────┬───────────────┘
                                ↓
                 ┌──────────────────────────────┐
                 │   STEP 3 — RERANK TO TOP-3   │
                 │  services/reranker.py         │
                 │  cross-encoder reads question │
                 │  + each chunk together        │
                 │  re-scores by true relevance  │
                 │  keeps only best 3 chunks     │
                 └──────────────┬───────────────┘
                                ↓
                 ┌──────────────────────────────┐
                 │  STEP 4 — BUILD RAG PROMPT   │
                 │  services/llm.py             │
                 │  combines top-3 chunks        │
                 │  + user question into         │
                 │  a structured prompt          │
                 └──────────────┬───────────────┘
                                ↓
                 ┌──────────────────────────────┐
                 │   STEP 5 — LLM GENERATION    │
                 │  Groq API (free)              │
                 │  Llama 3.3 70B model          │
                 │  generates thinking + answer  │
                 │  streams tokens back          │
                 └──────────────┬───────────────┘
                                ↓
                 ┌──────────────────────────────┐
                 │   STEP 6 — SSE STREAMING     │
                 │  FastAPI StreamingResponse    │
                 │  sends 3 types of events:     │
                 │  1. sources (immediately)     │
                 │  2. thinking chunks           │
                 │  3. answer text chunks        │
                 └──────────────┬───────────────┘
                                ↓
                 Frontend useChat.ts reads SSE stream
                 routes each event to correct component
                            ↓
                 ┌─────────────────────────────────┐
                 │  SourceCitations.tsx            │
                 │  shows which chunks were used   │
                 │  with match % scores            │
                 ├─────────────────────────────────┤
                 │  ThinkingPanel.tsx              │
                 │  collapsible reasoning trace    │
                 │  "View reasoning" button        │
                 ├─────────────────────────────────┤
                 │  MessageBubble.tsx              │
                 │  streams final answer           │
                 │  renders markdown               │
                 └─────────────────────────────────┘


Phase 3 — Data Storage (What lives where):

PostgreSQL (Render managed DB)
└── documents table
    ├── id (UUID)
    ├── filename
    ├── file_type (pdf/docx/xlsx/png/jpg)
    ├── session_id (identifies which user)
    ├── chunk_count
    ├── file_size
    ├── uploaded_at
    └── status (processing/ready/error)

ChromaDB (./chroma_db/ folder)
└── one collection per session
    └── each entry contains:
        ├── id (doc_id + chunk index)
        ├── embedding (384 numbers = the vector)
        ├── document (the actual chunk text)
        └── metadata
            ├── doc_id
            ├── filename
            └── chunk_index

./storage/ folder
└── original uploaded files saved as:
    └── {uuid}.{extension}
    e.g. 3f4a-91bc-....pdf


Phase 4 — Models Running Locally (no API cost):

all-MiniLM-L6-v2  (90 MB)
└── purpose: convert text to 384-dim vectors
└── used: during upload (chunks) and query (question)
└── runs: on your machine/Render server CPU
└── cost: $0

cross-encoder/ms-marco-MiniLM-L-6-v2  (90 MB)
└── purpose: rerank retrieved chunks by true relevance
└── used: after ChromaDB retrieval, before LLM call
└── runs: on your machine/Render server CPU
└── cost: $0

Groq API — Llama 3.3 70B
└── purpose: read context + generate final answer
└── used: once per chat message
└── runs: Groq cloud servers
└── cost: $0 (14,400 requests/day free)


One-line summary for your mentor:
"User uploads a document → it gets parsed, split into chunks, and each chunk is converted into a vector using a local AI model and stored in ChromaDB. When the user asks a question, the question is also converted to a vector, the most similar chunks are retrieved from ChromaDB, a reranker picks the best 3, and these are sent as context to an LLM which streams back a reasoned answer with source citations."