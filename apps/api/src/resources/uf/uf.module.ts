import { Module } from '@nestjs/common';
import { UfService } from './uf.service';
import { UfController } from './uf.controller';

@Module({
  controllers: [UfController],
  providers: [UfService],
  exports: [UfService],
})
export class UfModule {}
