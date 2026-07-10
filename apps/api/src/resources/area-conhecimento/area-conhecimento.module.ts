import { Module } from '@nestjs/common';
import { AreaConhecimentoService } from './area-conhecimento.service';
import { AreaConhecimentoController } from './area-conhecimento.controller';

@Module({
  controllers: [AreaConhecimentoController],
  providers: [AreaConhecimentoService],
  exports: [AreaConhecimentoService],
})
export class AreaConhecimentoModule {}
