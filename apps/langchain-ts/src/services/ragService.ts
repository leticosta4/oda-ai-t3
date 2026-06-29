import { ChatOpenAI, OpenAIEmbeddings } from "@langchain/openai";
import { PromptTemplate } from "@langchain/core/prompts";
import { RunnableSequence, RunnablePassthrough } from "@langchain/core/runnables";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { PrismaClient, prismaConfig } from '@oda/database';
import * as dotenv from "dotenv";

dotenv.config({ path: "../../.env" });

const prisma = new PrismaClient(prismaConfig);

const embeddings = new OpenAIEmbeddings({
  openAIApiKey: process.env.OPEN_AI_KEY,
  modelName: "text-embedding-3-small",
});

const model = new ChatOpenAI({
  openAIApiKey: process.env.OPEN_AI_KEY,
  modelName: "gpt-4o-mini",
  temperature: 0,
});

const ANSWER_PROMPT = PromptTemplate.fromTemplate(`
  Você é um assistente especializado em grupos de pesquisa do CNPq/DGP.
  Use as seguintes partes do contexto recuperado para responder à pergunta.
  Se você não sabe a resposta, apenas diga que não sabe, não tente inventar uma resposta.

  Contexto:
  {context}

  Pergunta: {question}

  Resposta (em português):`);

export async function askQuestion(question: string, chatHistory: string = "") {
  const [questionVector] = await embeddings.embedDocuments([question]);
  const vectorStr = `[${questionVector.join(',')}]`;
  const matchedChunks: any[] = await prisma.$queryRawUnsafe(
    `SELECT rc.conteudo 
     FROM rag_chunk rc 
     ORDER BY rc.embedding <-> $1::vector ASC 
     LIMIT 5`,
    vectorStr
  );

  const context = matchedChunks.map(c => c.conteudo).join('\n\n');
  const chain = RunnableSequence.from([
    {
      context: () => context,
      question: new RunnablePassthrough(),
    },
    ANSWER_PROMPT,
    model,
    new StringOutputParser(),
  ]);

  return await chain.invoke(question);
}

export async function ingestDocument(content: string, metadata: any = {}) {
  const docId = crypto.randomUUID ? crypto.randomUUID() : require('crypto').randomUUID();
  const doc = await prisma.ragDocument.create({
    data: {
      sourceType: 'PRODUCAO',
      sourceId: docId,
      titulo: metadata.titulo || "Documento Ingerido",
      conteudo: content,
      metadata
    }
  });

  const [vector] = await embeddings.embedDocuments([content]);
  const vectorStr = `[${vector.join(',')}]`;
  const chunkId = require('crypto').randomUUID();

  await prisma.$executeRawUnsafe(
    `INSERT INTO "rag_chunk" ("id", "document_id", "conteudo", "embedding", "ordem", "metadata", "atualizado_em") 
     VALUES ($1, $2, $3, $4::vector, $5, $6, NOW())`,
    chunkId, doc.id, content, vectorStr, 0, JSON.stringify(metadata)
  );

  return { success: true };
}

export async function ingestResearchGroup(data: any) {
  const nome = data.nome || "Desconhecido";
  const dgpId = data.id_dgp || "";

  let content = `Grupo de Pesquisa: ${nome}\n`;
  content += `DGP ID: ${dgpId}\n`;
  content += `Instituição: ${data.instituicao || ""}\n`;
  content += `Área: ${data.area || ""}\n`;
  content += `Ano de Formação: ${data.ano_formacao || ""}\n`;
  content += `Repercussão: ${data.repercussao || ""}\n`;

  const doc = await prisma.ragDocument.upsert({
    where: {
      sourceType_sourceId: {
        sourceType: 'GRUPO_PESQUISA',
        sourceId: dgpId,
      }
    },
    update: {
      titulo: nome,
      conteudo: content,
      metadata: data
    },
    create: {
      sourceType: 'GRUPO_PESQUISA',
      sourceId: dgpId,
      titulo: nome,
      conteudo: content,
      metadata: data
    }
  });

  await prisma.ragChunk.deleteMany({
    where: { documentId: doc.id }
  });

  const [vector] = await embeddings.embedDocuments([content]);
  const vectorStr = `[${vector.join(',')}]`;
  const chunkId = require('crypto').randomUUID();

  await prisma.$executeRawUnsafe(
    `INSERT INTO "rag_chunk" ("id", "document_id", "conteudo", "embedding", "ordem", "metadata", "atualizado_em") 
     VALUES ($1, $2, $3, $4::vector, $5, $6, NOW())`,
    chunkId, doc.id, content, vectorStr, 0, JSON.stringify(data)
  );

  return { success: true };
}
