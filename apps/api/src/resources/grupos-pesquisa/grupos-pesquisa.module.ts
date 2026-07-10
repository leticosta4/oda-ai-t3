import { Module } from '@nestjs/common';
import { GruposPesquisaService } from './grupos-pesquisa.service';
import { GruposPesquisaController } from './grupos-pesquisa.controller';
import { LangchainGatewayModule } from '../langchain/langchain.module';

import { PesquisadoresModule } from '../pesquisadores/pesquisadores.module';

@Module({
  imports: [LangchainGatewayModule, PesquisadoresModule],
  controllers: [GruposPesquisaController],
  providers: [GruposPesquisaService],
})
export class GruposPesquisaModule {}
