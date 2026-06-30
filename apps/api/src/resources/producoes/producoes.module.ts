import { Module } from '@nestjs/common';
import { ProducoesService } from './producoes.service';
import { ProducoesController } from './producoes.controller';
import { LangchainGatewayModule } from '../langchain/langchain.module';

@Module({
  imports: [LangchainGatewayModule],
  controllers: [ProducoesController],
  providers: [ProducoesService],
})
export class ProducoesModule {}
