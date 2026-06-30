import { Module } from '@nestjs/common';
import { PesquisadoresService } from './pesquisadores.service';
import { PesquisadoresController } from './pesquisadores.controller';
import { LangchainGatewayModule } from '../langchain/langchain.module';

@Module({
  imports: [LangchainGatewayModule],
  controllers: [PesquisadoresController],
  providers: [PesquisadoresService],
})
export class PesquisadoresModule {}
