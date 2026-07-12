import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db.client import db
from langchain_api.schemas import (
    QuestionRequest,
    SummarizeRequest,
    SemanticSearchRequest,
    IngestRequest,
)


from langchain_api.services import (
    ask_question_simple,
    ask_question_hybrid,
    ask_question_norag,
    summarize_text,
    perform_semantic_search,
    ingest_document,
    ingest_research_group,
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/question")
async def question_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question_hybrid(req.question, req.chatHistory)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question-simple")
async def question_simple_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question_simple(req.question, req.chatHistory)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question-norag")
async def question_norag_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question_norag(req.question, req.chatHistory)
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
            "createdAt": datetime.datetime.now().isoformat(),
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
            raise HTTPException(
                status_code=400, detail="Content or structured data is required"
            )

        res = await ingest_document(req.content, req.metadata or {})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("LANGCHAIN_PORT", 8002))
    uvicorn.run("langchain_api.main:app", host="0.0.0.0", port=port, reload=True)
