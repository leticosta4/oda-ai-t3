
import { PromptTemplate } from "@langchain/core/prompts";
import { ChatOpenAI, OpenAIEmbeddings } from "@langchain/openai";
import * as dotenv from 'dotenv';
import * as path from 'path';
dotenv.config({ path: path.resolve(__dirname, '../../../../.env') });

export const embeddings = new OpenAIEmbeddings({
  openAIApiKey: process.env.OPEN_AI_KEY,
  modelName: "text-embedding-3-small",
});


export const model = new ChatOpenAI({
  openAIApiKey: process.env.OPEN_AI_KEY,
  modelName: "gpt-4o-mini",
  temperature: 0,
});


export const ANSWER_PROMPT = PromptTemplate.fromTemplate(`
  Você é um assistente especializado em grupos de pesquisa do CNPq/DGP.
  Use as seguintes partes do contexto recuperado para responder à pergunta.
  Se você não sabe a resposta, apenas diga que não sabe, não tente inventar uma resposta.
  Você não precisa responder com todos os possíveis detalhes uma pergunta específica, seja mais direto.
  Contexto:
  {context}

  Pergunta: {question}

  Resposta (em português):`);


export const SUMMARIZE_PROMPT = PromptTemplate.fromTemplate(`
    Você é um assistente especializado em resumir textos acadêmicos e técnicos de forma clara.
    Instruções adicionais: {instructions}

    Texto a ser resumido:
    {text}

    Resumo (em português):`);