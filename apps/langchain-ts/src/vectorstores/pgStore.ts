import { PGVectorStore } from "@langchain/community/vectorstores/pgvector";
import { OpenAIEmbeddings } from "@langchain/openai";
import { PoolConfig } from "pg";
import * as dotenv from "dotenv";
import { embeddings } from "../core/config";

dotenv.config({ path: "../../.env" });

export const pgVectorConfig = {
  postgresConnectionOptions: {
    connectionString: process.env.DATABASE_URL,
  } as PoolConfig,
  tableName: "embeddings_v2",
  columns: {
    idColumnName: "id",
    vectorColumnName: "embedding",
    contentColumnName: "content",
    metadataColumnName: "metadata",
  },
};

let vectorStore: PGVectorStore | null = null;

export async function getVectorStore() {
  if (vectorStore) return vectorStore;

  vectorStore = await PGVectorStore.initialize(embeddings, pgVectorConfig);
  return vectorStore;
}
