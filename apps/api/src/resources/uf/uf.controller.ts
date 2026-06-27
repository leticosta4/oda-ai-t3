import { Controller, Get, Param, ParseUUIDPipe } from '@nestjs/common';
import { UfService } from './uf.service';

@Controller('uf')
export class UfController {
  constructor(private readonly ufService: UfService) {}

  @Get()
  findAll() {
    return this.ufService.findAll();
  }

  @Get(':id')
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.ufService.findById(id);
  }

  @Get('sigla/:sigla')
  findBySigla(@Param('sigla') sigla: string) {
    return this.ufService.findBySigla(sigla);
  }
}
