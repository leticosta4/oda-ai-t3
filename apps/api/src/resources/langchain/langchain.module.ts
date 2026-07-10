import { Module } from '@nestjs/common';
import { LangchainController } from './langchain.controller';
import { LangchainGatewayService } from './langchain.service';

@Module({
  controllers: [LangchainController],
  providers: [LangchainGatewayService],
  exports: [LangchainGatewayService],
})
export class LangchainGatewayModule {}
