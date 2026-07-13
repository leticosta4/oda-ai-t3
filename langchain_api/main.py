import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db.client import db
from langchain_api.schemas import QuestionRequest, QuestionResponse
from langchain_api.services import (
    ask_question_simple,
    ask_question_norag,
    ask_question_hybrid,
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


@app.post("/question-simple", response_model=QuestionResponse)
async def question_simple_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question_simple(req.question, req.chatHistory)
        return ans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question-hybrid", response_model=QuestionResponse)
async def question_hybrid_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question_hybrid(req.question, req.chatHistory)
        return ans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question-norag", response_model=QuestionResponse)
async def question_norag_endpoint(req: QuestionRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        ans = await ask_question_norag(req.question, req.chatHistory)
        return ans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("LANGCHAIN_PORT", 8002))
    uvicorn.run("langchain_api.main:app", host="0.0.0.0", port=port, reload=True)
