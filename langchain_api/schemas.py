from pydantic import BaseModel
from typing import Optional, Dict, Any

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
    id_dgp: Optional[str] = None
    nome: Optional[str] = None
    instituicao: Optional[str] = None
    area: Optional[str] = None
    ano_formacao: Optional[Any] = None
    repercussao: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
