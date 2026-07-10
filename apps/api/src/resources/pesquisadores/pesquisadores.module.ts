import { Module } from '@nestjs/common';
import { PesquisadoresService } from './pesquisadores.service';
import { PesquisadoresController } from './pesquisadores.controller';
import { LangchainGatewayModule } from '../langchain/langchain.module';
import { ProducoesModule } from '../producoes/producoes.module';

@Module({
  imports: [LangchainGatewayModule, ProducoesModule],
  controllers: [PesquisadoresController],
  providers: [PesquisadoresService],
  exports: [PesquisadoresService],
})
export class PesquisadoresModule {}
