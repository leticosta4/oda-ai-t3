export const LANGCHAIN_PATTERNS = {
  health: "langchain.health",
  generate: "langchain.generate",
  summarize: "langchain.summarize",
} as const;

export type LangchainProvider = "openai" | "local";

export interface LangchainGenerateRequest {
  prompt: string;
  system?: string;
  model?: string;
  temperature?: number;
}

export interface LangchainSummarizeRequest {
  text: string;
  instructions?: string;
  model?: string;
  temperature?: number;
}

export interface LangchainResponse {
  output: string;
  model: string;
  provider: LangchainProvider;
  createdAt: string;
}

export interface LangchainHealthResponse {
  status: "ok";
  transport: "tcp";
  provider: LangchainProvider;
  model: string;
}
