import { Injectable } from "@nestjs/common";
import { RpcException } from "@nestjs/microservices";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { ChatOpenAI } from "@langchain/openai";
import {
  LangchainGenerateRequest,
  LangchainHealthResponse,
  LangchainProvider,
  LangchainResponse,
  LangchainSummarizeRequest,
} from "./langchain.contracts";

const DEFAULT_MODEL = "gpt-4o-mini";

@Injectable()
export class LangchainService {
  health(): LangchainHealthResponse {
    return {
      status: "ok",
      transport: "tcp",
      provider: this.provider,
      model: this.defaultModel,
    };
  }

  async generate(
    request: LangchainGenerateRequest,
  ): Promise<LangchainResponse> {
    this.assertText(request.prompt, "prompt");

    const system =
      request.system ??
      "Voce e um assistente para apoiar buscas academicas e grupos de pesquisa.";

    return this.runChain({
      humanTemplate: "{prompt}",
      input: { prompt: request.prompt },
      system,
      model: request.model,
      temperature: request.temperature,
      localOutput: `Prompt recebido para processamento LangChain: ${request.prompt}`,
    });
  }

  async summarize(
    request: LangchainSummarizeRequest,
  ): Promise<LangchainResponse> {
    this.assertText(request.text, "text");

    const instructions =
      request.instructions ??
      "Resuma o texto em portugues, mantendo os pontos academicos mais relevantes.";

    return this.runChain({
      humanTemplate: "Instrucoes: {instructions}\n\nTexto:\n{text}",
      input: {
        instructions,
        text: request.text,
      },
      system:
        "Voce resume conteudos academicos com precisao, clareza e sem inventar informacoes.",
      model: request.model,
      temperature: request.temperature,
      localOutput: this.localSummary(request.text),
    });
  }

  private async runChain(params: {
    humanTemplate: string;
    input: Record<string, string>;
    system: string;
    model?: string;
    temperature?: number;
    localOutput: string;
  }): Promise<LangchainResponse> {
    const model = params.model ?? this.defaultModel;

    if (!process.env.OPENAI_API_KEY) {
      return {
        output: params.localOutput,
        model,
        provider: "local",
        createdAt: new Date().toISOString(),
      };
    }

    const prompt = ChatPromptTemplate.fromMessages([
      ["system", params.system],
      ["human", params.humanTemplate],
    ]);
    const chat = new ChatOpenAI({
      apiKey: process.env.OPENAI_API_KEY,
      model,
      temperature:
        params.temperature ?? Number(process.env.OPENAI_TEMPERATURE ?? 0.2),
    });
    const chain = prompt.pipe(chat).pipe(new StringOutputParser());
    const output = await chain.invoke(params.input);

    return {
      output,
      model,
      provider: "openai",
      createdAt: new Date().toISOString(),
    };
  }

  private assertText(value: string | undefined, field: string) {
    if (!value || value.trim().length === 0) {
      throw new RpcException(`Campo obrigatorio ausente: ${field}`);
    }
  }

  private localSummary(text: string) {
    const normalized = text.replace(/\s+/g, " ").trim();
    const preview =
      normalized.length > 480 ? `${normalized.slice(0, 477)}...` : normalized;

    return `Resumo local indisponivel sem OPENAI_API_KEY. Texto recebido: ${preview}`;
  }

  private get provider(): LangchainProvider {
    return process.env.OPENAI_API_KEY ? "openai" : "local";
  }

  private get defaultModel() {
    return process.env.OPENAI_MODEL ?? DEFAULT_MODEL;
  }
}
