import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { LangchainController } from "./langchain.controller";
import { LangchainService } from "./langchain.service";

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ".env",
    }),
  ],
  controllers: [LangchainController],
  providers: [LangchainService],
})
export class LangchainModule {}
