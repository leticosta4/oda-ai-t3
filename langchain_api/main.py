import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from db.client import db
import os

from langchain_api.services import (
    ask_question, summarize_text, perform_semantic_search,
    ingest_document, ingest_research_group
)

app = FastAPI(title="LangChain Python Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

class QuestionRequest(BaseModel):
    question: str
    chatHistory: Optional[str] = ""

class SummarizeRequest(BaseModel):
    text: str
    instructions: Optional[str] = None

class SemanticSearchRequest(BaseModel):
    query: str
    type: Optional[str] = None
    limit: Optional[int] = 10
    offset: Optional[int] = 0

class IngestRequest(BaseModel):
    # Can accept raw content/metadata or research group dictionary
    id_dgp: Optional[str] = None
    nome: Optional[str] = None
    instituicao: Optional[str] = None
    area: Optional[str] = None
    ano_formacao: Optional[Any] = None
    repercussao: Optional[str] = None
    
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/question")
async def question_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question(req.question, req.chatHistory)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize")
async def summarize_endpoint(req: SummarizeRequest):
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        output = await summarize_text(req.text, req.instructions)
        return {
            "output": output,
            "model": "gpt-4o-mini",
            "provider": "openai",
            "createdAt": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/semantic-search")
async def semantic_search_endpoint(req: SemanticSearchRequest):
    if not req.query:
        raise HTTPException(status_code=400, detail="Query is required")
    try:
        data = await perform_semantic_search(req.query, req.type, req.limit, req.offset)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_endpoint(req: IngestRequest):
    try:
        # Check if research group request
        if req.id_dgp or req.nome:
            group_data = req.dict(exclude_none=True)
            res = await ingest_research_group(group_data)
            return res
            
        if not req.content:
            raise HTTPException(status_code=400, detail="Content or structured data is required")
            
        res = await ingest_document(req.content, req.metadata or {})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("LANGCHAIN_PORT", 8002))
    uvicorn.run("langchain_api.main:app", host="0.0.0.0", port=port, reload=True)
