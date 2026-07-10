import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environments if not loaded
from dotenv import load_dotenv
load_dotenv()

embeddings = OpenAIEmbeddings(
    api_key=os.environ.get("OPEN_AI_KEY"),
    model="text-embedding-3-small"
)

model = ChatOpenAI(
    api_key=os.environ.get("OPEN_AI_KEY"),
    model="gpt-4o-mini",
    temperature=0
)

ANSWER_PROMPT = PromptTemplate.from_template("""
  Você é um assistente especializado em grupos de pesquisa do CNPq/DGP.
  Use as seguintes partes do contexto recuperado para responder à pergunta.
  Se você não sabe a resposta, apenas diga que não sabe, não tente inventar uma resposta.
  Você não precisa responder com todos os possíveis detalhes uma pergunta específica, seja mais direto.
  Contexto:
  {context}

  Pergunta: {question}

  Resposta (em português):""")

SUMMARIZE_PROMPT = PromptTemplate.from_template("""
    Você é um assistente especializado em resumir textos acadêmicos e técnicos de forma clara.
    Instruções adicionais: {instructions}

    Texto a ser resumido:
    {text}

    Resumo (em português):""")
