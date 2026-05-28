import { NestFactory } from "@nestjs/core";
import { MicroserviceOptions, Transport } from "@nestjs/microservices";
import { LangchainModule } from "./langchain.module";

async function bootstrap() {
  const host = process.env.LANGCHAIN_HOST ?? "127.0.0.1";
  const port = Number(process.env.LANGCHAIN_PORT ?? 8877);

  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    LangchainModule,
    {
      transport: Transport.TCP,
      options: {
        host,
        port,
      },
    },
  );

  await app.listen();
}

void bootstrap();
