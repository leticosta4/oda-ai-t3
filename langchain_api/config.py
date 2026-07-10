import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate

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
  
  REGRAS CRÍTICAS:
  1. Responda à pergunta com base estritamente no Contexto fornecido.
  2. Se o contexto fornecido for insuficiente para responder à pergunta de forma completa e segura, responda exatamente o seguinte: "Não encontrei informações suficientes sobre isso na base de dados de pesquisa."
  3. Não utilize conhecimentos externos ao contexto para fundamentar as afirmações.
  4. Seja direto e objetivo na sua resposta.

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
