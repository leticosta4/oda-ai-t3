import { Module } from '@nestjs/common';
import { LinhaPesquisaService } from './linha-pesquisa.service';
import { LinhaPesquisaController } from './linha-pesquisa.controller';
import { LangchainGatewayModule } from '../langchain/langchain.module';

@Module({
  imports: [LangchainGatewayModule],
  controllers: [LinhaPesquisaController],
  providers: [LinhaPesquisaService],
})
export class LinhaPesquisaModule {}
