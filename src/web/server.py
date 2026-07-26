from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.backend.weaviate_I.client import get_client
from src.llm.rag.embeddings.model import get_embedding_model
from src.llm.rag.pipeline import rag_model
from src.llm.rag.rag_agent.tools.make_retrieval import get_last_sources, reset_sources

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="RAG Assistant")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]


@app.on_event("startup")
def warm() -> None:
    """Load the embedder and Weaviate client once, before serving traffic."""
    get_embedding_model()
    get_client()


def _dedupe(sources: list[dict]) -> list[dict]:
    """Collapse repeated (file, page) grounding chunks, keeping first occurrence."""
    seen = set()
    unique = []
    for source in sources:
        key = (source["source_file"], source["page"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run one grounded RAG turn and return the answer with its citations."""
    reset_sources()
    answer = "".join(rag_model(request.history, request.message))
    return ChatResponse(answer=answer, sources=_dedupe(get_last_sources()))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
