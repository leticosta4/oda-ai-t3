import { PrismaPg } from '@prisma/adapter-pg';
export * from '../generated/prisma/index.js';
import path from "path";
import fs from "fs";
import dotenv from "dotenv";

function loadEnv() {
  if (process.env.DATABASE_URL) {
    console.log("[Database] DATABASE_URL já definida:", process.env.DATABASE_URL);
    return;
  }
  let currentDir = process.cwd();
  console.log("[Database] Iniciando busca do .env a partir de:", currentDir);
  for (let i = 0; i < 5; i++) {
    const envPath = path.resolve(currentDir, '.env');
    console.log("[Database] Tentando:", envPath);
    if (fs.existsSync(envPath)) {
      dotenv.config({ path: envPath });
      console.log("[Database] .env carregado de:", envPath);
      console.log("[Database] DATABASE_URL resolvida:", process.env.DATABASE_URL);
      return;
    }
    const parentDir = path.dirname(currentDir);
    if (parentDir === currentDir) {
      break;
    }
    currentDir = parentDir;
  }
  console.warn("[Database] AVISO: .env não encontrado a partir do CWD!");
}

loadEnv();


export const prismaConfig = {
  adapter: new PrismaPg({
    connectionString: process.env.DATABASE_URL,
  }),
};